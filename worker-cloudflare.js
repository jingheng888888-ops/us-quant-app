// AlphaSniper Cloudflare Worker
// Deploy this file to Cloudflare Workers, then put the Worker URL into the app settings.
// Endpoints:
//   /chart?symbol=NVDA&interval=5m&range=5d
//   /universe?limit=5000

const CORE = ['NVDA','MSFT','AAPL','AMZN','META','GOOGL','TSLA','AMD','AVGO','MRVL','AMAT','LRCX','MU','KLAC','QCOM','TSM','ASML','ARM','INTC','SMCI','DELL','VRT','ETN','GEV','HUBB','POWL','ANET','CRWD','PANW','PLTR','SNOW','APP','COIN','HOOD','MSTR','NFLX','ORCL','ADBE','NOW','SHOP','UBER','ABNB','COST','WMT','JPM','GS','BAC','XOM','LLY','UNH','CAT','BA','GE','NOC','RTX','PWR','MYRG','NVT','COHR','ALAB','CRDO','CLS','CELH','ELF','RCL','CCL','NCLH','FSLR','ENPH','ON','MPWR','TER','TXN','ADI','WDC','STX'];
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Cache-Control': 'no-store'
};

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') return new Response(null, {headers:CORS});
    const url = new URL(request.url);
    try {
      if (url.pathname === '/chart') return await handleChart(url);
      if (url.pathname === '/universe') return await handleUniverse(url);
      if (url.pathname === '/' || url.pathname === '/health') return json({ok:true, name:'AlphaSniper Worker', time:new Date().toISOString()});
      return json({error:'not_found'}, 404);
    } catch (err) {
      return json({error:String(err && err.message || err)}, 500);
    }
  }
};

function json(obj, status=200){ return new Response(JSON.stringify(obj), {status, headers:{...CORS, 'Content-Type':'application/json; charset=utf-8'}}); }

async function handleChart(url){
  const symbol = (url.searchParams.get('symbol') || 'NVDA').toUpperCase().replace(/[^A-Z0-9.\-]/g,'');
  const interval = url.searchParams.get('interval') || '5m';
  const range = url.searchParams.get('range') || '5d';
  const y = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=${encodeURIComponent(interval)}&range=${encodeURIComponent(range)}&includePrePost=true`;
  const res = await fetch(y, {headers:{'User-Agent':'Mozilla/5.0 AlphaSniper/1.0', 'Accept':'application/json'}});
  const txt = await res.text();
  return new Response(txt, {status:res.status, headers:{...CORS, 'Content-Type':'application/json; charset=utf-8'}});
}

async function handleUniverse(url){
  const limit = Math.min(Number(url.searchParams.get('limit')||5000), 8000);
  const all = new Set(CORE);
  const exchanges = ['NASDAQ','NYSE','AMEX'];
  for (const ex of exchanges) {
    try {
      const api = `https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=${limit}&exchange=${ex}`;
      const res = await fetch(api, {headers:{
        'User-Agent':'Mozilla/5.0 AlphaSniper/1.0',
        'Accept':'application/json,text/plain,*/*',
        'Origin':'https://www.nasdaq.com',
        'Referer':'https://www.nasdaq.com/market-activity/stocks/screener'
      }});
      if (!res.ok) continue;
      const j = await res.json();
      const rows = j?.data?.table?.rows || [];
      for (const r of rows) {
        const sym = String(r.symbol || '').trim().toUpperCase();
        if (/^[A-Z][A-Z0-9.\-]{0,7}$/.test(sym) && !sym.includes('^')) all.add(sym);
      }
    } catch(e) {}
  }
  return json({symbols:[...all].slice(0, limit), fallback: all.size <= CORE.length});
}
