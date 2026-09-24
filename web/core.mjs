export const rules = [
['New account cash-out',28,['account_age'],(p,e)=>p.direction==='withdrawal'&&e.account_age<30&&p.cents>100000,'Account under 30 days; withdrawal over $1,000'],
['Velocity spike',30,['tx_count_1h'],(p,e)=>e.tx_count_1h>=8,'At least 8 payments in the prior hour'],
['Rapid cash-out',32,['minutes_since_deposit'],(p,e)=>p.direction==='withdrawal'&&p.cents>50000&&e.minutes_since_deposit<=30,'Withdrawal over $500 within 30 minutes of deposit'],
['Authentication pressure',25,['failed_logins'],(p,e)=>e.failed_logins>=4,'At least 4 failed logins'],
['Identity reset',30,['device_trusted','password_reset','customer_devices'],(p,e)=>!e.device_trusted&&e.password_reset&&e.customer_devices>=1,'Untrusted device after reset with reported device count'],
['Impossible travel',30,['distance_km','hours_since_last_location'],(p,e)=>e.distance_km>500&&e.distance_km/e.hours_since_last_location>900,'Over 500 km at implied speed over 900 km/h'],
['Shared device network',32,['shared_accounts'],(p,e)=>e.shared_accounts>=3,'At least 3 accounts share a device'],
['Ownership mismatch',28,['ownership_match'],(p,e)=>!e.ownership_match,'Reported ownership does not match'],
['Chargeback history',25,['prior_chargebacks'],(p,e)=>e.prior_chargebacks>=2,'At least 2 prior chargebacks'],
['Risky destination',26,['recipient_risk','recipient_age'],(p,e)=>e.recipient_risk==='high'&&e.recipient_age<=30,'High-risk recipient at most 30 days old'],
['Proxy and deviation',24,['vpn_proxy','customer_avg_amount'],(p,e)=>e.vpn_proxy&&p.cents/100/e.customer_avg_amount>3,'Proxy use and amount over 3× baseline'],
['Amount outlier',28,['customer_avg_amount'],(p,e)=>p.cents/100/e.customer_avg_amount>=6,'Amount at least 6× baseline']
];
const bounds={account_age:[0,36500,1],customer_avg_amount:[Number.MIN_VALUE,1e9],tx_count_1h:[0,1e6,1],minutes_since_deposit:[0,1e8],failed_logins:[0,1e5,1],customer_devices:[1,1e5,1],distance_km:[0,50000],hours_since_last_location:[Number.MIN_VALUE,1e7],shared_accounts:[1,1e6,1],prior_chargebacks:[0,1e5,1],recipient_age:[0,36500,1]};
const bools=['device_trusted','password_reset','ownership_match','vpn_proxy'];
export function validate(raw){
 const p={};
 for(const key of ['external_id','customer_ref']){p[key]=String(raw[key]??'').trim();if(!/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$/.test(p[key]))throw Error(`${key.replaceAll('_',' ')} must use 1–80 letters, numbers, dots, colons, underscores or hyphens.`);}
 const amount=String(raw.amount??'').trim();if(!/^\d{1,10}(\.\d{1,2})?$/.test(amount))throw Error('Use a positive USD amount with at most two decimal places.');
 p.cents=Number(amount.split('.')[0])*100+Number((amount.split('.')[1]||'').padEnd(2,'0'));if(p.cents<=0||p.cents>1e11)throw Error('Amount must be between $0.01 and $1 billion.');
 if(raw.currency&&raw.currency!=='USD')throw Error('Only USD is supported.');
 p.direction=raw.direction;if(!['deposit','withdrawal'].includes(p.direction))throw Error('Direction must be deposit or withdrawal.');
 p.status=raw.status||'pending';if(!['pending','settled','blocked','returned'].includes(p.status))throw Error('Invalid payment status.');
 const date=String(raw.occurred_at||'');if(!/^\d{4}-\d\d-\d\dT.*(?:Z|[+-]\d\d:\d\d)$/.test(date)||!Number.isFinite(Date.parse(date))||Date.parse(date)>Date.now())throw Error('Payment time must be a past ISO date with timezone.');p.occurred_at=new Date(date).toISOString();
 let e=raw.evidence||{};if(typeof e==='string'){try{e=JSON.parse(e);}catch{throw Error('Evidence must be valid JSON.');}}
 if(!e||typeof e!=='object'||Array.isArray(e))throw Error('Evidence must be a JSON object.');
 p.evidence={};for(const [k,v] of Object.entries(e)){if(v===null)continue;if(Object.hasOwn(bounds,k)){const [min,max,int]=bounds[k];if(typeof v!=='number'||!Number.isFinite(v)||v<min||v>max||(int&&!Number.isInteger(v)))throw Error(`Invalid evidence: ${k}.`);}else if(bools.includes(k)){if(typeof v!=='boolean')throw Error(`${k} must be true or false.`);}else if(k==='recipient_risk'){if(!['low','medium','high'].includes(v))throw Error('Invalid recipient risk.');}else throw Error(`Unknown evidence field: ${k}.`);p.evidence[k]=v;}
 return p;
}
export function assess(p){let evaluated=0;const signals=[];rules.forEach(([name,weight,fields,predicate],i)=>{if(fields.every(f=>p.evidence[f]!==undefined&&p.evidence[f]!==null)){evaluated++;if(predicate(p,p.evidence))signals.push({id:`R${String(i+1).padStart(2,'0')}`,name,weight});}});return {evaluated,signals,score:evaluated?Math.min(100,signals.reduce((a,s)=>a+s.weight,0)):null};}
export function batch(raw,existing=[]){if(!raw.length||raw.length>5000)throw Error('Import between 1 and 5,000 payments.');if(existing.length+raw.length>10000)throw Error('This browser workspace supports up to 10,000 payments.');const ids=new Set(existing.map(p=>p.external_id));return raw.map((r,i)=>{let p;try{p=validate(r);}catch(e){throw Error(`Row ${i+1}: ${e.message}`);}if(ids.has(p.external_id))throw Error(`Row ${i+1}: duplicate payment reference.`);ids.add(p.external_id);return p;});}
export function parseCSV(text){
 text=text.replace(/^\uFEFF/,'');const rows=[];let row=[],cell='',quoted=false,closed=false;
 for(let i=0;i<text.length;i++){const c=text[i];if(quoted){if(c==='"'){if(text[i+1]==='"'){cell+='"';i++;}else{quoted=false;closed=true;}}else cell+=c;}else if(c===','||c==='\n'||c==='\r'){row.push(cell);cell='';closed=false;if(c!==','){if(c==='\r'&&text[i+1]==='\n')i++;if(row.some(x=>x!==''))rows.push(row);row=[];}}else if(c==='"'&&cell===''&&!closed){quoted=true;}else{if(closed||c==='"')throw Error('Malformed CSV quoting.');cell+=c;}}
 if(quoted)throw Error('Unclosed CSV quote.');row.push(cell);if(row.some(x=>x!==''))rows.push(row);if(rows.length<2)throw Error('CSV needs a header and at least one payment.');const headers=rows.shift().map(h=>h.trim());if(new Set(headers).size!==headers.length)throw Error('Duplicate CSV headers.');const allowed=['external_id','customer_ref','occurred_at','amount','direction','status','currency','evidence'];if(headers.some(h=>!allowed.includes(h)))throw Error('Unsupported CSV column. Use the provided template.');for(const h of allowed.slice(0,5))if(!headers.includes(h))throw Error(`Missing column: ${h}`);return rows.map(r=>{if(r.length!==headers.length)throw Error('CSV row has the wrong number of columns.');return Object.fromEntries(headers.map((h,i)=>[h,r[i]]));});
}
export function csvCell(value){const s=String(value??'');return '"'+(/^[=+\-@\t\r\n]/.test(s)?"'":'')+s.replaceAll('"','""')+'"';}
export function restore(raw){
 if(!Array.isArray(raw?.payments)||raw.payments.length>10000||!raw.cases||typeof raw.cases!=='object'||Array.isArray(raw.cases))throw Error('Invalid backup.');
 const payments=[];for(let i=0;i<raw.payments.length;i+=5000)payments.push(...batch(raw.payments.slice(i,i+5000).map(p=>({...p,amount:(p.cents/100).toFixed(2)})),payments));
 const cases={};const ids=new Set(payments.map(p=>p.external_id));const valid=h=>h&&typeof h.note==='string'&&h.note.length<=2000&&['open','in review','escalated','closed'].includes(h.status)&&Number.isFinite(Date.parse(h.updated));
 for(const [id,c] of Object.entries(raw.cases)){if(!ids.has(id)||!valid(c)||!Array.isArray(c.history)||c.history.some(h=>!valid(h)))throw Error('Invalid investigation in backup.');cases[id]={status:c.status,note:c.note,updated:c.updated,history:c.history.map(h=>({status:h.status,note:h.note,updated:h.updated}))};}
 return {payments,cases,revision:raw.revision||0};
}
