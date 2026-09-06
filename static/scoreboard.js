/* Optional blockchain integration through an injected Ethereum wallet. */
let scoreboardConfig = null;
let feedbackRequest = Promise.resolve(false);
let scoreboardRun = 0;
let scoreboardRefresh = 0;
let registrationBusy = false;
let registrationComplete = false;

function syncRegisterButton() {
    const button = document.getElementById('registerResult');
    button.hidden = !feedbackGiven || !scoreboardConfig || !scoreboardConfig.enabled;
    button.disabled = registrationBusy || registrationComplete || !scoreboardConfig || !scoreboardConfig.ready;
}

async function refreshScoreboard(connect = false) {
    const version = ++scoreboardRefresh;
    const health = document.getElementById('scoreboardHealth');
    const account = document.getElementById('scoreboardAccount');
    const totals = document.getElementById('scoreboardTotals');
    totals.hidden = true;
    account.textContent = '';
    health.textContent = 'Verificando rede e contrato…';
    if (scoreboardConfig) scoreboardConfig.ready = false;
    syncRegisterButton();
    try {
        const response = await fetch('/scoreboard/config', {cache: 'no-store'});
        const config = await response.json();
        if (version !== scoreboardRefresh) return false;
        scoreboardConfig = config;
        syncRegisterButton();
        if (!response.ok || !config.ready) throw new Error(config.error || 'Placar indisponível.');
        document.getElementById('registerResult').textContent = 'Registrar resultado em ' + config.chainName;
        health.textContent = config.chainName + ' · Rede e contrato verificados';
        if (!window.ethereum) {
            account.textContent = 'Use uma carteira Ethereum no navegador para consultar seu placar.';
            return true;
        }
        const accounts = await window.ethereum.request({method: connect ? 'eth_requestAccounts' : 'eth_accounts'});
        if (version !== scoreboardRefresh) return false;
        if (!accounts.length) {
            account.textContent = 'Conecte sua carteira para consultar os resultados registrados.';
            return true;
        }
        const player = accounts[0];
        account.textContent = 'Carteira: ' + player + ' · Consultando ' + config.chainName;
        // Reads use the validated server RPC, regardless of the wallet's selected network.
        const scoresResponse = await fetch('/scoreboard/scores/' + encodeURIComponent(player), {cache: 'no-store'});
        const scores = await scoresResponse.json();
        if (version !== scoreboardRefresh) return false;
        if (!scoresResponse.ok) throw new Error(scores.error || 'Erro ao consultar placar.');
        document.getElementById('chainGames').textContent = scores.games;
        document.getElementById('chainCorrect').textContent = scores.correctGuesses;
        document.getElementById('chainQuestions').textContent = scores.totalQuestions;
        totals.hidden = false;
        return true;
    } catch (error) {
        if (version !== scoreboardRefresh) return false;
        health.textContent = error.code === 4001 ? 'Conexão cancelada na carteira.' : error.message;
        if (scoreboardConfig) {
            scoreboardConfig.ready = false;
            if (scoreboardConfig.enabled) document.getElementById('onchainPanel').open = true;
        }
        syncRegisterButton();
        return false;
    }
}

function resetScoreboard() {
    scoreboardRun++;
    registrationBusy = false;
    registrationComplete = false;
    document.getElementById('registerResult').hidden = true;
    document.getElementById('registerResult').disabled = false;
    document.getElementById('chainStatus').textContent = '';
}

async function recordOnChain() {
    const button = document.getElementById('registerResult');
    const status = document.getElementById('chainStatus');
    const run = scoreboardRun;
    if (registrationBusy || registrationComplete) return;
    registrationBusy = true;
    button.disabled = true;
    const update = text => { if (run === scoreboardRun) status.textContent = text; };
    try {
        if (!await feedbackRequest) throw new Error('Não foi possível confirmar o resultado no servidor.');
        if (!await refreshScoreboard()) throw new Error('Placar indisponível. Consulte o estado da rede e tente atualizar.');
        if (run !== scoreboardRun) return;
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
                await wallet.request({method: 'wallet_switchEthereumChain', params: [{chainId: scoreboardConfig.chainId}]});
            }
        }
        if (await wallet.request({method: 'eth_chainId'}) !== scoreboardConfig.chainId)
            throw new Error('Selecione a rede ' + scoreboardConfig.chainName + ' na carteira.');
        if (run !== scoreboardRun) return;
        const response = await fetch('/scoreboard/transaction', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({player})
        });
        const tx = await response.json();
        if (!response.ok) throw new Error(tx.error);
        if (run !== scoreboardRun) return;
        const code = await wallet.request({method: 'eth_getCode', params: [tx.to, 'latest']});
        if (code === '0x' || code === '0x0') throw new Error('Contrato não encontrado. Implante o placar na rede configurada.');
        update('Confirme o registro na carteira. Será usado ETH de teste.');
        const hash = await wallet.request({method: 'eth_sendTransaction', params: [{from: player, ...tx}]});
        if (run !== scoreboardRun) return;
        registrationComplete = true; // Keep registration disabled while the submitted transaction is pending.
        update('Transação enviada: ' + hash + '. Aguardando confirmação…');
        for (let attempt = 0; attempt < 60; attempt++) {
            if (run !== scoreboardRun) return;
            if (await wallet.request({method: 'eth_chainId'}) !== scoreboardConfig.chainId)
                throw new Error('Rede alterada. Confira a transação na carteira.');
            const receipt = await wallet.request({method: 'eth_getTransactionReceipt', params: [hash]});
            if (run !== scoreboardRun) return;
            if (receipt) {
                if (receipt.status !== '0x1') {
                    registrationComplete = false;
                    throw new Error('Transação revertida. O resultado pode já estar registrado.');
                }
                registrationComplete = true;
                update('Resultado registrado em ' + scoreboardConfig.chainName + '! Transação: ' + hash);
                await refreshScoreboard();
                return;
            }
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        update('Transação ainda pendente. Acompanhe pela carteira: ' + hash);
    } catch (error) {
        update(error.code === 4001 ? 'Solicitação cancelada na carteira.' : (error.message || 'Erro ao registrar resultado.'));
    } finally {
        if (run === scoreboardRun) {
            registrationBusy = false;
            syncRegisterButton();
        }
    }
}

if (window.ethereum && typeof window.ethereum.on === 'function') {
    window.ethereum.on('accountsChanged', () => refreshScoreboard());
    window.ethereum.on('chainChanged', () => refreshScoreboard());
    window.ethereum.on('disconnect', () => {
        scoreboardRefresh++;
        document.getElementById('scoreboardTotals').hidden = true;
        document.getElementById('scoreboardAccount').textContent = 'Carteira desconectada.';
    });
}
refreshScoreboard();
