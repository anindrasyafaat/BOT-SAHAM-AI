const fs=require('fs');for(const a of process.argv.slice(2)){const j=JSON.parse(fs.readFileSync(a+'.out.json'));let i=0,r=0,w=0,o=0;
for(const m of Object.values(j.modelUsage)){i+=m.inputTokens;r+=m.cacheReadInputTokens;w+=m.cacheCreationInputTokens;o+=m.outputTokens}
console.log(a.split('/').pop().padEnd(11),'turns',String(j.num_turns).padStart(3),' $'+j.total_cost_usd.toFixed(3),' inTotal',((i+r+w)/1e3).toFixed(0)+'k','write',(w/1e3).toFixed(0)+'k','read',(r/1e3).toFixed(0)+'k','out',o,' |',(j.result||'').slice(0,90))}
