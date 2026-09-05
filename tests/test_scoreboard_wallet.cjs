const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync('static/scoreboard.js', 'utf8');
async function scenario(reject) {
    const elements = { registerResult: {hidden: true, disabled: false}, chainStatus: {textContent: ''} };
    const calls = [];
    const config = {enabled: true, chainId: '0x7a69', chainName: 'Anvil local', rpcUrl: 'http://127.0.0.1:8545'};
    const context = vm.createContext({
        document: {getElementById: id => elements[id]}, feedbackGiven: true,
        setTimeout, Promise,
        fetch: async url => ({ok: true, json: async () => url.endsWith('config') ? config : {to: '0x1234', data: '0xabcd', value: '0x0', chainId: '0x7a69'}}),
        window: {ethereum: {request: async ({method}) => {
            calls.push(method);
            if (method === 'eth_requestAccounts') return ['0x5678'];
            if (method === 'eth_chainId') return '0x7a69';
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
    console.log('2 wallet tests passed (confirmed transaction and user rejection).');
})().catch(e => { console.error(e); process.exitCode = 1; });
