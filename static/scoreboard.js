/* Optional local Anvil integration through an injected Ethereum wallet. */
let scoreboardConfig = null;
let feedbackRequest = Promise.resolve(false);
let scoreboardRun = 0;

function resetScoreboard() {
    scoreboardRun++;
    document.getElementById('registerResult').hidden = true;
    document.getElementById('registerResult').disabled = false;
    document.getElementById('chainStatus').textContent = '';
}

async function recordOnChain() {
    const button = document.getElementById('registerResult');
    const status = document.getElementById('chainStatus');
    const run = scoreboardRun;
    button.disabled = true;
    const update = text => { if (run === scoreboardRun) status.textContent = text; };
    try {
        if (!await feedbackRequest) throw new Error('Não foi possível confirmar o resultado no servidor.');
        if (!window.ethereum) throw new Error('Abra em um navegador com carteira Ethereum, como MetaMask.');
        const wallet = window.ethereum;
        const accounts = await wallet.request({ method: 'eth_requestAccounts' });
        const player = accounts[0];
        if (!player) throw new Error('Nenhuma conta selecionada.');
        const chain = await wallet.request({ method: 'eth_chainId' });
        if (chain !== scoreboardConfig.chainId) {
            try {
                await wallet.request({method: 'wallet_switchEthereumChain', params: [{chainId: scoreboardConfig.chainId}]});
            } catch (error) {
                if (error.code !== 4902) throw error;
                await wallet.request({method: 'wallet_addEthereumChain', params: [{
                    chainId: scoreboardConfig.chainId, chainName: scoreboardConfig.chainName,
                    rpcUrls: [scoreboardConfig.rpcUrl], nativeCurrency: {name: 'Ether de teste', symbol: 'ETH', decimals: 18}
                }]});
            }
        }
        if (await wallet.request({method: 'eth_chainId'}) !== scoreboardConfig.chainId)
            throw new Error('Selecione a rede Anvil local na carteira.');
        if (run !== scoreboardRun) return;
        const response = await fetch('/scoreboard/transaction', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({player})
        });
        const tx = await response.json();
        if (!response.ok) throw new Error(tx.error);
        if (run !== scoreboardRun) return;
        const code = await wallet.request({method: 'eth_getCode', params: [tx.to, 'latest']});
        if (code === '0x' || code === '0x0') throw new Error('Contrato não encontrado. Implante o placar na rede local.');
        update('Confirme o registro na carteira. Será usado ETH de teste.');
        const hash = await wallet.request({method: 'eth_sendTransaction', params: [{from: player, ...tx}]});
        update('Transação enviada: ' + hash + '. Aguardando confirmação…');
        for (let attempt = 0; attempt < 60; attempt++) {
            if (run !== scoreboardRun) return;
            if (await wallet.request({method: 'eth_chainId'}) !== scoreboardConfig.chainId)
                throw new Error('Rede alterada. Confira a transação na carteira.');
            const receipt = await wallet.request({method: 'eth_getTransactionReceipt', params: [hash]});
            if (receipt) {
                if (receipt.status !== '0x1') throw new Error('Transação revertida. O resultado pode já estar registrado.');
                update('Resultado registrado na Anvil! Transação: ' + hash);
                return;
            }
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        update('Transação ainda pendente. Acompanhe pela carteira: ' + hash);
    } catch (error) {
        update(error.code === 4001 ? 'Solicitação cancelada na carteira.' : (error.message || 'Erro ao registrar resultado.'));
        if (run === scoreboardRun) button.disabled = false;
    }
}

fetch('/scoreboard/config').then(r => r.json()).then(config => {
    scoreboardConfig = config;
    if (config.enabled && feedbackGiven) document.getElementById('registerResult').hidden = false;
}).catch(() => {});
