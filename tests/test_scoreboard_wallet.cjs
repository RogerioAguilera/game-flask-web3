const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync('static/scoreboard.js', 'utf8');
async function scenario(reject, addNetwork = false, anvil = false, sepolia = false) {
    const elements = { registerResult: {hidden: true, disabled: false}, chainStatus: {textContent: ''} };
    for (const id of ['scoreboardHealth', 'scoreboardAccount', 'scoreboardTotals', 'chainGames', 'chainCorrect', 'chainQuestions']) elements[id] = {textContent: '', hidden: true};
    const calls = [];
    const config = {enabled: true, ready: true, chainId: sepolia ? '0xaa36a7' : anvil ? '0x7a69' : '0x539', chainName: sepolia ? 'Sepolia' : anvil ? 'Anvil local' : 'Ganache local', rpcUrl: sepolia ? 'https://ethereum-sepolia-rpc.publicnode.com' : anvil ? 'http://127.0.0.1:8545' : 'http://127.0.0.1:7545'};
    let activeChain = addNetwork ? '0x1' : config.chainId;
    let known = !addNetwork;
    const context = vm.createContext({
        document: {getElementById: id => elements[id]}, feedbackGiven: true,
        setTimeout, Promise,
        fetch: async url => ({ok: true, json: async () => url.endsWith('config') ? {...config} : url.includes('/scores/') ? {games: '2', correctGuesses: '1', totalQuestions: '7'} : {to: '0x1234', data: '0xabcd', value: '0x0', chainId: config.chainId}}),
        window: {ethereum: {request: async ({method, params}) => {
            calls.push(method);
            if (method === 'eth_requestAccounts' || method === 'eth_accounts') return ['0x5678'];
            if (method === 'eth_chainId') return activeChain;
            if (method === 'wallet_switchEthereumChain') {
                assert.strictEqual(params[0].chainId, config.chainId);
                if (!known) throw {code: 4902};
                activeChain = config.chainId;
                return null;
            }
            if (method === 'wallet_addEthereumChain') {
                assert.strictEqual(params[0].rpcUrls[0], config.rpcUrl);
                assert.strictEqual(params[0].chainName, config.chainName);
                known = true;
                return null;
            }
            if (method === 'eth_getCode') return '0x1234';
            if (method === 'eth_sendTransaction') {
                if (reject) throw {code: 4001};
                return '0xhash';
            }
            if (method === 'eth_getTransactionReceipt') return {status: '0x1'};
            throw Error(method);
        }}}
    });
    vm.runInContext(source, context);
    await new Promise(resolve => setImmediate(resolve));
    await vm.runInContext('feedbackRequest = Promise.resolve(true); recordOnChain()', context);
    assert(elements.registerResult.textContent.includes(config.chainName));
    if (addNetwork) assert(calls.includes('wallet_addEthereumChain'));
    if (reject) {
        assert(elements.chainStatus.textContent.includes('cancelada'));
        assert.strictEqual(elements.registerResult.disabled, false);
        assert(!calls.includes('eth_getTransactionReceipt'));
    } else {
        assert(elements.chainStatus.textContent.includes('Resultado registrado'));
        assert.strictEqual(elements.chainGames.textContent, '2');
        assert.strictEqual(elements.scoreboardTotals.hidden, false);
        assert.strictEqual(elements.registerResult.disabled, true);
        assert(calls.includes('eth_getTransactionReceipt'));
    }
}
async function accountChangesAndOutage() {
    const elements = {};
    const handlers = {};
    const pending = {};
    let offline = false;
    let player = 'wallet-one';
    const config = {enabled: true, ready: true, chainName: 'Ganache local', chainId: '0x539'};
    const context = vm.createContext({
        document: {getElementById: id => elements[id] || (elements[id] = {hidden: false, textContent: ''})},
        feedbackGiven: true, setTimeout, Promise,
        fetch: async url => {
            if (url.endsWith('config')) return {ok: true, json: async () => ({...config, ready: !offline, error: 'Rede indisponível'})};
            return new Promise(resolve => { pending[url] = resolve; });
        },
        window: {ethereum: {
            on: (name, callback) => {handlers[name] = callback;},
            request: async () => player ? [player] : []
        }}
    });
    vm.runInContext(source, context);
    const flush = () => new Promise(resolve => setImmediate(resolve));
    await flush();
    player = 'wallet-two';
    handlers.accountsChanged();
    await flush();
    pending['/scoreboard/scores/wallet-two']({ok: true, json: async () => ({games: '2', correctGuesses: '1', totalQuestions: '6'})});
    await flush();
    pending['/scoreboard/scores/wallet-one']({ok: true, json: async () => ({games: '99', correctGuesses: '99', totalQuestions: '99'})});
    await flush();
    assert.strictEqual(elements.chainGames.textContent, '2', 'Old wallet response must not overwrite new wallet');
    player = null;
    handlers.accountsChanged();
    await flush();
    assert.strictEqual(elements.scoreboardTotals.hidden, true);
    offline = true;
    await vm.runInContext('refreshScoreboard()', context);
    assert.strictEqual(elements.registerResult.disabled, true);
    assert.strictEqual(elements.scoreboardTotals.hidden, true);
    assert(elements.scoreboardHealth.textContent.includes('indisponível'));
    offline = false;
    await vm.runInContext('refreshScoreboard()', context);
    assert.strictEqual(elements.registerResult.disabled, false);
}
(async () => {
    await scenario(false);
    await scenario(true);
    await scenario(false, true);
    await scenario(false, false, true);
    await scenario(false, true, false, true);
    await accountChangesAndOutage();
    console.log('6 wallet scenarios passed, including stale responses, disconnect and outage recovery.');
})().catch(e => { console.error(e); process.exitCode = 1; });
