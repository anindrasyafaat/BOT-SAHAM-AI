// Generates a fixture project: 3 big files, one planted off-by-one bug in applyDiscount, and a test.
const fs=require('fs'),path=require('path');const dir=process.argv[2];fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(path.join(dir,'src'),{recursive:true});
const filler=(p,n)=>Array.from({length:n},(_,i)=>`function ${p}Helper${i}(x) {\n  // helper ${i}: normalises input for ${p} module\n  const v = Number(x) || 0;\n  return v * ${i%7+1} + ${i%13};\n}\n`).join('\n');
fs.writeFileSync(path.join(dir,'src/pricing.js'),filler('price',700)+`
const TIERS = ['bronze', 'silver', 'gold', 'platinum'];
const RATES = [0.05, 0.10, 0.20, 0.30];
function applyDiscount(amount, tier) {
  const idx = TIERS.indexOf(tier);
  if (idx < 0) return amount;
  return Math.round(amount * (1 - RATES[idx + 1]) * 100) / 100;
}
`+filler('pricing2',700)+`\nmodule.exports = { applyDiscount };\n`);
fs.writeFileSync(path.join(dir,'src/orders.js'),filler('order',900)+`\nmodule.exports = {};\n`);
fs.writeFileSync(path.join(dir,'src/users.js'),filler('user',900)+`\nmodule.exports = {};\n`);
fs.writeFileSync(path.join(dir,'test.js'),`const a=require('assert');const {applyDiscount}=require('./src/pricing');a.strictEqual(applyDiscount(100,'gold'),80);a.strictEqual(applyDiscount(100,'bronze'),95);a.strictEqual(applyDiscount(100,'platinum'),70);a.strictEqual(applyDiscount(100,'x'),100);console.log('PASS');\n`);
