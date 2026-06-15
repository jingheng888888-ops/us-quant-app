const DEFAULT_WORKER = '';
const CORE = ['NVDA','MSFT','AAPL','AMZN','META','GOOGL','TSLA','AMD','AVGO','MRVL','AMAT','LRCX','MU','KLAC','QCOM','TSM','ASML','ARM','INTC','SMCI','DELL','VRT','ETN','GEV','HUBB','POWL','ANET','CRWD','PANW','PLTR','SNOW','APP','COIN','HOOD','MSTR','NFLX','ORCL','ADBE','NOW','SHOP','UBER','ABNB','COST','WMT','JPM','GS','BAC','XOM','LLY','UNH','CAT','BA','GE','NOC','RTX','PWR','MYRG','NVT','COHR','ALAB','CRDO','CLS','CELH','ELF','RCL','CCL','NCLH','FSLR','ENPH','ON','MPWR','TER','TXN','ADI','WDC','STX'];
const AI = ['NVDA','AMD','AVGO','MRVL','AMAT','LRCX','MU','TSM','ASML','ARM','QCOM','SMCI','DELL','VRT','ETN','GEV','POWL','HUBB','PWR','MYRG','NVT','ANET','COHR','ALAB','CRDO','CLS','PLTR','APP','SNOW','CRWD','PANW','MDB','DDOG','NET','AI','SOUN'];
const SECTOR = {NVDA:'AI/GPU',AMD:'AI芯片',AVGO:'AI芯片/网络',MRVL:'高速互联',AMAT:'半导体设备',LRCX:'半导体设备',MU:'HBM/存储',TSM:'晶圆代工',ASML:'光刻设备',ARM:'芯片架构',QCOM:'芯片',SMCI:'AI服务器',DELL:'AI服务器',VRT:'AI电力散热',ETN:'AI电力设备',GEV:'电力设备',POWL:'配电/开关柜',HUBB:'电网设备',PWR:'电网工程',MYRG:'电网工程',NVT:'电气系统',ANET:'AI网络设备',COHR:'光通信',ALAB:'高速互联',CRDO:'高速互联',CLS:'服务器供应链'};
let results = [];
let selected = null;
let filter = 'all';
let marketCtx = {qqq:null, spy:null, gate:'UNKNOWN'};

const $ = id => document.getElementById(id);
const fmt = (n,d=2)=> Number.isFinite(n) ? Number(n).toFixed(d) : '--';
const money = n => Number.isFinite(n) ? '$' + Number(n).toFixed(2) : '--';
const pct = n => Number.isFinite(n) ? (n>=0?'+':'') + Number(n).toFixed(2)+'%' : '--';
const sleep = ms => new Promise(r=>setTimeout(r,ms));

function init(){
  $('workerUrl').value = localStorage.getItem('workerUrl') || DEFAULT_WORKER;
  const drawer = $('settingsDrawer');
  const openDrawer = () => { drawer.hidden = false; drawer.style.display = 'flex'; };
  const closeDrawer = () => { drawer.hidden = true; drawer.style.display = 'none'; };
  closeDrawer();
  $('openSettings').onclick = openDrawer;
  $('closeSettings').onclick = closeDrawer;
  drawer.addEventListener('click', (e)=>{ if(e.target === drawer) closeDrawer(); });
  $('saveSettings').onclick = () => { localStorage.setItem('workerUrl',$('workerUrl').value.trim()); alert('已保存'); closeDrawer(); };
  $('testWorker').onclick = testWorker;
  $('scanBtn').onclick = runScan;
  $('quickBtn').onclick = () => { $('scanMode').value='core'; $('scanLimit').value='30'; runScan(); };
  document.querySelectorAll('.tab').forEach(btn=>btn.onclick=()=>{document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));btn.classList.add('active');filter=btn.dataset.filter;renderCards();});
  renderCards();
}

function workerBase(){ return (localStorage.getItem('workerUrl') || $('workerUrl').value || DEFAULT_WORKER || '').replace(/\/$/,''); }
function endpoint(path){ const base=workerBase(); return base ? base+path : path; }

async function fetchJson(url, timeout=9000){
  const ctrl = new AbortController();
  const timer = setTimeout(()=>ctrl.abort(), timeout);
  try{
    const res = await fetch(url, {signal:ctrl.signal, cache:'no-store'});
    if(!res.ok) throw new Error('HTTP '+res.status);
    return await res.json();
  } finally { clearTimeout(timer); }
}

async function yahooChart(symbol, interval='5m', range='5d'){
  const qs = `symbol=${encodeURIComponent(symbol)}&interval=${interval}&range=${range}`;
  const base = workerBase();
  if(base){ return await fetchJson(`${base}/chart?${qs}`, 12000); }
  // Direct Yahoo may be blocked by CORS on GitHub Pages/Safari. Worker is recommended.
  return await fetchJson(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=${interval}&range=${range}&includePrePost=true`, 12000);
}

async function universe(){
  const mode = $('scanMode').value;
  if(mode==='custom') return ($('customSymbols').value||'').split(',').map(s=>s.trim().toUpperCase()).filter(Boolean);
  if(mode==='ai') return AI;
  if(mode==='full' && workerBase()){
    try{
      const j = await fetchJson(`${workerBase()}/universe?limit=5000`, 15000);
      if(j && Array.isArray(j.symbols) && j.symbols.length) return j.symbols;
    }catch(e){ console.warn('universe fallback',e); }
  }
  return CORE;
}

function ema(values, len){
  const out=[]; const k=2/(len+1); let prev=null;
  for(const v of values){ if(!Number.isFinite(v)){out.push(prev);continue;} prev = prev==null ? v : v*k + prev*(1-k); out.push(prev); }
  return out;
}
function sma(values,len){ const out=[]; let sum=0; for(let i=0;i<values.length;i++){sum+=values[i]||0; if(i>=len) sum-=values[i-len]||0; out.push(i>=len-1?sum/len:null);} return out; }
function atr(bars,len=14){
  const tr=[];
  for(let i=0;i<bars.length;i++){
    const b=bars[i], p=bars[i-1];
    const prev = p ? p.c : b.c;
    tr.push(Math.max(b.h-b.l, Math.abs(b.h-prev), Math.abs(b.l-prev)));
  }
  return sma(tr,len);
}
function vwap(bars){
  let pv=0, vol=0;
  for(const b of bars){ if(Number.isFinite(b.c) && Number.isFinite(b.v)){ const tp=(b.h+b.l+b.c)/3; pv+=tp*b.v; vol+=b.v; } }
  return vol>0 ? pv/vol : null;
}
function parseChart(j){
  const r = j?.chart?.result?.[0]; if(!r) throw new Error(j?.chart?.error?.description || 'no chart');
  const q = r.indicators?.quote?.[0]; const ts = r.timestamp || [];
  const bars = ts.map((t,i)=>({
    t:t*1000,
    o:q.open?.[i], h:q.high?.[i], l:q.low?.[i], c:q.close?.[i], v:q.volume?.[i]||0
  })).filter(b=>Number.isFinite(b.c)&&Number.isFinite(b.h)&&Number.isFinite(b.l));
  return {bars, meta:r.meta||{}};
}
function last(arr){ return arr[arr.length-1]; }
function agg30(bars){
  const out=[];
  for(let i=0;i<bars.length;i+=6){
    const chunk=bars.slice(i,i+6); if(chunk.length<3) continue;
    out.push({t:chunk[0].t,o:chunk[0].o,h:Math.max(...chunk.map(b=>b.h)),l:Math.min(...chunk.map(b=>b.l)),c:last(chunk).c,v:chunk.reduce((a,b)=>a+b.v,0)});
  }
  return out;
}
function todayBars(bars){
  if(!bars.length) return [];
  const d = new Date(last(bars).t).toDateString();
  return bars.filter(b=>new Date(b.t).toDateString()===d);
}

async function scoreSymbol(symbol, qqqChange, settings){
  const five = parseChart(await yahooChart(symbol,'5m','5d'));
  if(five.bars.length < 45) throw new Error('5m历史不足');
  const daily = parseChart(await yahooChart(symbol,'1d','6mo'));
  if(daily.bars.length < 60) throw new Error('日线历史不足');
  const bars = five.bars;
  const tb = todayBars(bars); const use = tb.length>=12 ? tb : bars.slice(-80);
  const cls = bars.map(b=>b.c), vols=bars.map(b=>b.v);
  const price = last(bars).c;
  const prevClose = five.meta.chartPreviousClose || bars[Math.max(0,bars.length-use.length-1)]?.c || bars[0].c;
  const changePct = (price/prevClose-1)*100;
  if(price < settings.minPrice) throw new Error('低于最低股价');
  const ema20 = last(ema(cls,20)), ema50=last(ema(cls,50));
  const vw = vwap(use);
  const atrArr = atr(bars,14); const a = last(atrArr);
  if(!Number.isFinite(a) || a<=0) throw new Error('ATR无法计算');
  const dollar5 = bars.slice(-1)[0].v * price;
  const avgVol20 = sma(vols,20); const avgv = last(avgVol20) || 1;
  const rvol = last(bars).v / avgv;
  const lastBar = last(bars);
  const body = Math.abs(lastBar.c-lastBar.o); const range = Math.max(0.0001,lastBar.h-lastBar.l);
  const upperWick = (lastBar.h - Math.max(lastBar.c,lastBar.o))/range;
  const thirty = agg30(bars.slice(-120)); const tCls=thirty.map(b=>b.c); const tEma20=last(ema(tCls,20)); const tEma50=last(ema(tCls,50));
  const dCls = daily.bars.map(b=>b.c); const dEma20=last(ema(dCls,20)); const dEma50=last(ema(dCls,50)); const dHigh52 = Math.max(...daily.bars.slice(-252).map(b=>b.h));
  const distVWAP = vw ? (price - vw) / a : 0;
  const rs = Number.isFinite(qqqChange) ? changePct - qqqChange : null;
  let score=0; const positives=[]; const risks=[]; const checks=[];
  function add(cond, pts, text, fail){ if(cond){score+=pts; positives.push(text); checks.push({text,pass:true});} else { if(fail) risks.push(fail); checks.push({text:fail||text,pass:false}); } }
  add(price>vw,10,'5m站上VWAP','5m未站上VWAP');
  add(price>ema20,10,'5m站上EMA20','5m未站上EMA20');
  add(price>ema50,10,'5m站上EMA50','5m未站上EMA50');
  add(thirty.length>20 && price>tEma20,8,'30m结构在EMA20上方','30m结构不强');
  add(thirty.length>20 && price>tEma50,7,'30m结构在EMA50上方','30m中线结构偏弱');
  add(price>dEma20,8,'日线站上EMA20','日线未站上EMA20');
  add(price>dEma50,7,'日线站上EMA50','日线未站上EMA50');
  if(dHigh52 && price > dHigh52*0.88){ score+=5; positives.push('接近52周强势区'); }
  if(Number.isFinite(rs) && rs>0){ score+=10; positives.push(`强于QQQ ${fmt(rs,2)}%`); } else risks.push('相对QQQ不占优');
  if(rvol>1.2){ score+=12; positives.push(`相对成交量 ${fmt(rvol,2)}x`); } else if(rvol>0.8){ score+=6; positives.push('量能尚可'); } else risks.push('量能不足');
  if(dollar5>=settings.minDollar){ score+=10; positives.push('最近5分钟成交额达标'); } else risks.push('最近5分钟成交额不足');
  if(changePct>0){ score+=5; positives.push('日内动量为正'); }
  if(SECTOR[symbol]) score+=5;
  // risk penalties
  let severe=false;
  if(distVWAP>3.5){ score-=25; risks.push('极端远离VWAP，禁止追高'); severe=true; }
  else if(distVWAP>2.5){ score-=15; risks.push('远离VWAP，等待回踩'); }
  if(upperWick>0.55 && rvol>1.2){ score-=12; risks.push('放量长上影，疑似抛压'); }
  const dayOpen = use[0]?.o; const gapPct = dayOpen && prevClose ? (dayOpen/prevClose-1)*100 : 0;
  if(gapPct>12){ score-=10; risks.push(`跳空过大 ${fmt(gapPct,1)}%，降低仓位`); }
  if(price<vw){ score-=10; }
  score=Math.max(0,Math.min(100,Math.round(score)));
  const ref = Math.max(vw||price, ema20||price);
  let buyLow = ref - 0.35*a;
  let buyHigh = ref + 0.45*a;
  const chaseLine = buyHigh + 0.55*a;
  const stop = Math.min(ref - 1.2*a, price - 1.35*a);
  const risk = price - stop;
  const target1 = price + risk*1.35;
  const target2 = price + risk*2.15;
  const rr = risk>0 ? (target1-price)/risk : 0;
  const inBuy = price>=buyLow && price<=buyHigh;
  const notChase = price<=chaseLine && !severe;
  const liquid = dollar5>=settings.minDollar;
  let status='FORBID', action='禁止：条件不足，等待重新扫描。';
  if(!liquid){ status='FORBID'; action='禁止：成交额不足，手动下单风险大。'; }
  else if(score>=82 && inBuy && notChase && rr>=1.2){ status='BUY'; action='可买：价格在买入区，按计划小心执行，禁止超追高线追。'; }
  else if(score>=78 && !inBuy && price>buyHigh && notChase){ status='PULLBACK'; action=`等回踩：好票但偏高，等回到 ${money(buyLow)}-${money(buyHigh)}。`; }
  else if(score>=75 && !notChase){ status='PULLBACK'; action='等回踩：趋势强但远离VWAP，禁止追高。'; }
  else if(score>=70 && risks.length<=4){ status='WATCH'; action='观察：有强度但条件不完整，等突破或回踩确认。'; }
  else if(score>=65){ status='BREAKOUT'; action='等突破：需要重新站上关键均线/VWAP。'; }
  else { status='FORBID'; action='禁止：评分不足或结构不合格。'; }
  const shares = risk>0 ? Math.max(0, Math.floor((settings.account*settings.riskPct/100)/risk)) : 0;
  return {symbol, sector:SECTOR[symbol]||'股票', status, statusText:statusCn(status), action, score, price, changePct, buyLow,buyHigh,chaseLine,stop,target1,target2,shares, risk, rr, atr:a, vwap:vw, ema20, ema50, rvol, dollar5, positives:positives.slice(0,6), risks:risks.slice(0,6), checks, ts:Date.now()};
}
function statusCn(s){ return {BUY:'🟢 可买',PULLBACK:'🟡 等回踩',WATCH:'🔍 观察',BREAKOUT:'🔵 等突破',SMALL:'🟠 小仓试',FORBID:'🔴 禁止'}[s]||s; }

async function scanMarketCtx(){
  try{
    const q = await scoreSymbol('QQQ', 0, {minPrice:1,minDollar:1000,account:100000,riskPct:1});
    const s = await scoreSymbol('SPY', 0, {minPrice:1,minDollar:1000,account:100000,riskPct:1});
    marketCtx.qqq=q; marketCtx.spy=s;
    marketCtx.gate = (q.price>q.ema20 && s.price>s.ema20) ? 'OPEN' : 'CAUTION';
    $('qqqVal').textContent = `${money(q.price)} ${pct(q.changePct)}`; $('qqqVal').className=q.changePct>=0?'up':'down';
    $('spyVal').textContent = `${money(s.price)} ${pct(s.changePct)}`; $('spyVal').className=s.changePct>=0?'up':'down';
    $('gateVal').textContent = marketCtx.gate==='OPEN'?'允许':'谨慎'; $('gateVal').className=marketCtx.gate==='OPEN'?'up':'down';
    $('gateReason').textContent = marketCtx.gate==='OPEN'?'QQQ/SPY短线结构正常':'大盘结构一般，降低仓位';
  }catch(e){
    $('gateVal').textContent='未知'; $('gateReason').textContent='大盘数据获取失败';
  }
}

async function runScan(){
  const t0=performance.now();
  $('scanBtn').disabled=true; $('scanBtn').textContent='扫描中...'; $('scanMsg').textContent='正在获取行情，不要反复点击。';
  results=[]; renderCards();
  const settings={
    minPrice:Number($('minPrice').value)||5,
    minDollar:1000000,
    account:Number($('accountSize').value)||100000,
    riskPct:Number($('riskPct').value)||1
  };
  try{
    await scanMarketCtx();
    let syms = await universe();
    const limit = Number($('scanLimit').value)||50;
    syms = [...new Set(syms.map(s=>s.toUpperCase()).filter(Boolean))].slice(0, limit);
    let valid=0; let done=0; const out=[];
    const qqqChg = marketCtx.qqq?.changePct ?? 0;
    const concurrency = 6;
    async function worker(){
      while(syms.length){
        const sym = syms.shift();
        try{
          const r = await scoreSymbol(sym, qqqChg, settings);
          if(r.status!=='FORBID' || r.score>=45) out.push(r);
          valid++;
        }catch(e){
          out.push({symbol:sym, sector:SECTOR[sym]||'股票', status:'FORBID', statusText:'🔴 禁止', score:0, action:'数据不足：'+e.message, price:null, changePct:null, positives:[], risks:[e.message], checks:[]});
        }
        done++;
        if(done%3===0){ $('scanMsg').textContent=`扫描中：${done}/${done+syms.length}`; }
      }
    }
    await Promise.race([
      Promise.all(Array.from({length:concurrency}, worker)),
      (async()=>{await sleep(45000); throw new Error('扫描超时：免费源太慢，请降低扫描数量或配置Worker');})()
    ]);
    results = out.sort((a,b)=>(rankStatus(a.status)-rankStatus(b.status)) || b.score-a.score).slice(0,60);
    $('statScanned').textContent = done;
    $('statValid').textContent = valid;
    $('statBuy').textContent = results.filter(r=>r.status==='BUY').length;
    $('statTime').textContent = ((performance.now()-t0)/1000).toFixed(1)+'s';
    $('lastUpdate').textContent = new Date().toLocaleString();
    $('scanMsg').textContent = `扫描完成：输出 ${results.length} 只。只看可买/等回踩，别追高。`;
    renderCards();
  }catch(e){
    $('scanMsg').textContent = '扫描失败：' + e.message + '。如果你在 GitHub Pages 上用，请配置 Cloudflare Worker。';
  }finally{
    $('scanBtn').disabled=false; $('scanBtn').textContent='开始扫描';
  }
}
function rankStatus(s){ return {BUY:0,PULLBACK:1,WATCH:2,BREAKOUT:3,SMALL:4,FORBID:5}[s] ?? 9; }

function renderCards(){
  const box=$('cards'); box.innerHTML='';
  const list = results.filter(r=>filter==='all'||r.status===filter);
  if(!list.length){ box.innerHTML='<div class="empty-detail">暂无结果。点击开始扫描。</div>'; return; }
  for(const r of list){
    const el=document.createElement('div'); el.className='stock-card '+(selected?.symbol===r.symbol?'active':'');
    el.onclick=()=>{selected=r; renderCards(); renderDetail(r);};
    el.innerHTML=`
      <div class="card-top">
        <div><div class="sym">${r.symbol}</div><div class="name">${r.sector||''}</div></div>
        <div class="badge ${r.status}">${r.statusText}</div>
      </div>
      <div class="card-metrics">
        <div class="metric"><span>分数</span><b>${r.score ?? 0}</b></div>
        <div class="metric"><span>现价</span><b>${money(r.price)}</b></div>
        <div class="metric"><span>涨跌</span><b class="${(r.changePct||0)>=0?'up':'down'}">${pct(r.changePct)}</b></div>
        <div class="metric"><span>止损</span><b>${money(r.stop)}</b></div>
      </div>
      <div class="reason">${r.action || ''}</div>`;
    box.appendChild(el);
  }
  if(!selected && list[0]) { selected=list[0]; renderDetail(selected); }
}

function renderDetail(r){
  const p=$('detailPanel');
  const manualId = 'manualPrice';
  p.innerHTML=`
    <div class="detail-head">
      <div><h2>${r.symbol}</h2><div class="muted">${r.sector||''}</div><div class="detail-price">${money(r.price)} <span class="${(r.changePct||0)>=0?'up':'down'}">${pct(r.changePct)}</span></div></div>
      <div class="scorebox"><span class="muted">综合分</span><br><b>${r.score ?? 0}</b><span>/100</span><br><div class="badge ${r.status}">${r.statusText}</div></div>
    </div>
    <div class="action-box">${r.action||''}</div>
    <div class="manual-box"><input id="${manualId}" type="number" step="0.01" placeholder="输入券商真实现价重算"><button id="recalcBtn">重算</button></div>
    <div class="plan-grid">
      <div class="plan-item"><span>买入区</span><b>${money(r.buyLow)} - ${money(r.buyHigh)}</b></div>
      <div class="plan-item"><span>禁止追高线</span><b>${money(r.chaseLine)}</b></div>
      <div class="plan-item"><span>硬止损</span><b>${money(r.stop)}</b></div>
      <div class="plan-item"><span>止盈1</span><b>${money(r.target1)}</b></div>
      <div class="plan-item"><span>止盈2</span><b>${money(r.target2)}</b></div>
      <div class="plan-item"><span>建议股数</span><b>${r.shares||0} 股</b></div>
      <div class="plan-item"><span>ATR / VWAP</span><b>${fmt(r.atr)} / ${money(r.vwap)}</b></div>
      <div class="plan-item"><span>RVOL</span><b>${fmt(r.rvol,2)}x</b></div>
    </div>
    <div class="detail-section"><h3>为什么选/不选</h3><div class="bullets">${(r.positives||[]).map(x=>`<div class="bullet">✅ ${x}</div>`).join('') || '<div class="bullet">无明显优势</div>'}</div></div>
    <div class="detail-section"><h3>风险提示</h3><div class="bullets">${(r.risks||[]).map(x=>`<div class="bullet">⚠️ ${x}</div>`).join('') || '<div class="bullet">暂未发现主要风险</div>'}</div></div>
    <div class="detail-section"><h3>TradingView K线</h3><div class="tv-wrap"><iframe src="${tvUrl(r.symbol)}" allowfullscreen></iframe></div></div>`;
  $('recalcBtn').onclick=()=>manualRecalc(r, Number($(manualId).value));
}
function manualRecalc(r, price){
  if(!Number.isFinite(price)||price<=0){ alert('请输入有效价格'); return; }
  const nr={...r, price};
  const ref = Math.max(nr.vwap||price, nr.ema20||price);
  const a = nr.atr || price*0.02;
  nr.buyLow = ref - .35*a; nr.buyHigh = ref + .45*a; nr.chaseLine = nr.buyHigh + .55*a;
  nr.stop = Math.min(ref - 1.2*a, price - 1.35*a);
  const risk = price - nr.stop;
  nr.target1 = price + risk*1.35; nr.target2 = price + risk*2.15;
  const account=Number($('accountSize').value)||100000, rp=Number($('riskPct').value)||1;
  nr.shares = risk>0 ? Math.floor((account*rp/100)/risk) : 0;
  nr.action = '已按券商现价重算。下单前再核对买入区、止损、止盈。';
  selected=nr; renderDetail(nr);
}
function tvUrl(sym){
  const s = encodeURIComponent('NASDAQ:'+sym);
  const cfg = encodeURIComponent(JSON.stringify({autosize:true,symbol:'NASDAQ:'+sym,interval:'5',timezone:'America/New_York',theme:'dark',style:'1',locale:'zh_CN',hide_top_toolbar:false,hide_legend:false,allow_symbol_change:true,calendar:false,support_host:'https://www.tradingview.com'}));
  return `https://s.tradingview.com/widgetembed/?frameElementId=tv_${s}&symbol=${s}&interval=5&hidesidetoolbar=1&symboledit=1&saveimage=0&toolbarbg=rgba(0,0,0,1)&studies=[]&theme=dark&style=1&timezone=America%2FNew_York&withdateranges=1&hidevolume=0&locale=zh_CN`;
}
async function testWorker(){
  $('testResult').textContent='测试中...';
  try{
    const j=await yahooChart('NVDA','5m','1d');
    const p=parseChart(j); $('testResult').textContent=`连接成功\nNVDA bars: ${p.bars.length}\nlast: ${money(last(p.bars).c)}`;
  }catch(e){ $('testResult').textContent='连接失败：'+e.message+'\n建议部署 worker-cloudflare.js，然后填入 Worker 地址。'; }
}

init();
