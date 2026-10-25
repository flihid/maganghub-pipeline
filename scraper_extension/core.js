(() => {
  const DAY = 86400000;
  const defaults = {
    query: '(maganghub OR "magang hub" OR "magang nasional" OR "magang kemnaker" OR "pemagangan nasional")',
    language: 'in',
    phases: [
      {name:'fase1_pengumuman', since:'2026-07-01', until:'2026-09-01'},
      {name:'fase2_seleksi', since:'2026-09-01', until:'2026-09-21'},
      {name:'fase3_penempatan', since:'2026-09-21', until:'2026-10-26'}
    ],
    pilotPerPhase: 100, maxRaw: 10000, maxPerDay: 150,
    scrollDelayMs: 6500, queryDelayMs: 35000, idleRounds: 8
  };
  const iso = value => new Date(value).toISOString().slice(0,10);
  function validate(c) {
    if (!c.query || !/^[a-z]{2,3}$/.test(c.language)) throw Error('Kueri/bahasa tidak valid');
    if (!Array.isArray(c.phases) || !c.phases.length) throw Error('Fase belum diisi');
    const names = new Set();
    c.phases.forEach((p,i) => {
      if (!/^fase\d+_[a-z_]+$/.test(p.name) || names.has(p.name)) throw Error('Nama fase tidak valid/duplikat');
      names.add(p.name);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(p.since) || !/^\d{4}-\d{2}-\d{2}$/.test(p.until) ||
          iso(p.since)!==p.since || iso(p.until)!==p.until || p.since>=p.until) throw Error('Tanggal fase tidak valid');
      if (i && c.phases[i-1].until!==p.since) throw Error('Fase harus berurutan dan bersebelahan');
    });
    for (const key of ['pilotPerPhase','maxRaw','maxPerDay','idleRounds'])
      if (!Number.isInteger(c[key]) || c[key]<1) throw Error(key+' harus bilangan bulat positif');
    if (c.scrollDelayMs<5000 || c.queryDelayMs<25000) throw Error('Jeda minimum: scroll 5000 ms, kueri 25000 ms');
    return c;
  }
  function jobs(c) {
    validate(c);
    const lists=c.phases.map(p => {
      const out=[];
      for(let d=Date.parse(p.until)-DAY; d>=Date.parse(p.since); d-=DAY)
        out.push({fase:p.name,since:iso(d),until:iso(d+DAY)});
      return out;
    });
    const out=[];
    for(let n=0;n<Math.max(...lists.map(x=>x.length));n++)
      for(const list of lists) if(list[n]) out.push(list[n]);
    return out.map((j,i)=>({...j,index:i,id:[c.query,c.language,j.since,j.until].join('|')}));
  }
  function wibDate(t) {
    const value=Date.parse(t);
    if(!Number.isFinite(value) || !/(Z|[+-]\d\d:\d\d)$/.test(t)) return null;
    return iso(value+7*3600000);
  }
  function phaseOf(c,t) { const d=wibDate(t);return d?c.phases.find(p=>p.since<=d&&d<p.until)?.name:null; }
  function inJob(j,t) {const d=wibDate(t);return !!d&&j.since<=d&&d<j.until;}
  function query(c,j) {return `${c.query} lang:${c.language} since:${j.since} until:${j.until}`;}
  function url(c,j) {return 'https://x.com/search?'+new URLSearchParams({q:query(c,j),src:'typed_query',f:'live'});}
  function metric(label) {
    if(!label) return null;
    const m=/^([\d,]+)(?:\.([\d]+))?\s*([KM])?\b/i.exec(label);
    if(!m) return null;
    const n=Number(m[1].replaceAll(',','')+(m[2]?'.'+m[2]:''));
    return m[3]?Math.round(n*({K:1000,M:1000000}[m[3].toUpperCase()])):Number.isInteger(n)?n:null;
  }
  globalThis.MagangHubCore={defaults,validate,jobs,wibDate,phaseOf,inJob,query,url,metric};
})();
