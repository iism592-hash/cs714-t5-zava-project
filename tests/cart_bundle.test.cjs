const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/shared/static/chat.js', 'utf8');
const code = source.slice(source.indexOf('let bundleAddInProgress'), source.indexOf('function attachCartActions'));
async function run() {
 const added = [];
 const context = {lastRecommendedProducts:[{name:'Cordless Drill'},{name:'Safety Glasses'}], loadedProducts:[], fetch:async()=>({ok:true,json:async()=>({products:[{product_name:'Benchtop Drill',base_price:395},{product_name:'Cordless Drill',base_price:171.64}]})}),addToCart:p=>added.push(p),updateCartUI:()=>{},showToast:()=>{},console};
 vm.createContext(context);vm.runInContext(code,context);
 const result = await vm.runInContext('executeAddAllToCart()',context);
 assert.equal(added.length,1);assert.equal(added[0].base_price,171.64);assert.equal(result.unavailable[0],'Safety Glasses');
 context.fetch=async()=>({ok:false,status:503});context.lastRecommendedProducts=[{name:'Level'}];
 const failed=await vm.runInContext('executeAddAllToCart()',context);assert.equal(failed.added.length,0);assert.equal(added.length,1);
 console.log('PASS: exact catalog matching, missing products, request errors; no fabricated items');
}
run().catch(e=>{console.error(e);process.exitCode=1});
