const {test} = require('node:test');
const assert = require('node:assert/strict');
const {matchOrder} = require('./match.cjs');
const rows = [
  {id:'a1',storeId:'A',email:'buyer@example.com',orderNumber:'#0012'},
  {id:'a2',storeId:'A',email:'buyer@example.com',orderNumber:'#0013'},
  {id:'b1',storeId:'B',email:'buyer@example.com',orderNumber:'#0012'},
  {id:'blank',storeId:'A',email:null,orderNumber:'#0014'}
];
const query = {storeId:'A',email:'buyer@example.com',orderNumber:'#0012'};
test('selects the exact candidate within the specified store', () => assert.deepEqual(matchOrder(rows,query),{status:'candidate',ids:['a1']}));
test('multiple orders require a choice instead of the first record', () => assert.deepEqual(matchOrder(rows,{...query,orderNumber:undefined}),{status:'ambiguous',ids:['a1','a2']}));
test('a conflicting order reference does not fall back to email', () => assert.equal(matchOrder(rows,{...query,orderNumber:'#9999'}).status,'no-match'));
test('blank email never matches an order with no email', () => assert.equal(matchOrder(rows,{...query,email:' '}).status,'insufficient-input'));
test('missing store is insufficient input', () => assert.equal(matchOrder(rows,{...query,storeId:undefined}).status,'insufficient-input'));
test('email whitespace and case normalize under the documented policy', () => assert.deepEqual(matchOrder(rows,{...query,email:' BUYER@example.com '}),{status:'candidate',ids:['a1']}));
test('order identifiers retain leading zeros', () => assert.equal(matchOrder(rows,{...query,orderNumber:'#12'}).status,'no-match'));
test('plus aliases are not merged', () => assert.equal(matchOrder(rows,{...query,email:'buyer+other@example.com'}).status,'no-match'));
test('duplicate candidate records remain ambiguous', () => assert.equal(matchOrder([...rows,rows[0]],query).status,'ambiguous'));
test('an empty result is not an invented candidate', () => assert.deepEqual(matchOrder([],query),{status:'no-match',ids:[]}));
