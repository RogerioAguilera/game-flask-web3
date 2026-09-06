const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync('static/scoreboard.js', 'utf8');
async function scenario(reject, addNetwork = false, anvil = false) {
    const elements = { registerResult: {hidden: true, disabled: false}, chainStatus: {textContent: ''} };
    const calls = [];
    const config = {enabled: true, chainId: anvil ? '0x7a69' : '0x539', chainName: anvil ? 'Anvil local' : 'Ganache local', rpcUrl: anvil ? 'http://127.0.0.1:8545' : 'http://127.0.0.1:7545'};
    let activeChain = addNetwork ? '0x1' : config.chainId;
    let known = !addNetwork;
    const context = vm.createContext({
        document: {getElementById: id => elements[id]}, feedbackGiven: true,
        setTimeout, Promise,
        fetch: async url => ({ok: true, json: async () => url.endsWith('config') ? config : {to: '0x1234', data: '0xabcd', value: '0x0', chainId: config.chainId}}),
        window: {ethereum: {request: async ({method, params}) => {
            calls.push(method);
            if (method === 'eth_requestAccounts') return ['0x5678'];
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
        assert.strictEqual(elements.registerResult.disabled, true);
        assert(calls.includes('eth_getTransactionReceipt'));
    }
}
(async () => {
    await scenario(false);
    await scenario(true);
    await scenario(false, true);
    await scenario(false, false, true);
    console.log('4 wallet tests passed (Ganache, Anvil, rejection, network addition/switch).');
})().catch(e => { console.error(e); process.exitCode = 1; });
