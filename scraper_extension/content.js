(() => {
  const C=globalThis.MagangHubCore;
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  let running=false, cancelled=false;
  const render=n=>!n?'':n.nodeType===3?n.textContent:n.nodeType===1&&n.tagName==='IMG'?
    (n.getAttribute('alt')||''):Array.from(n.childNodes||[]).map(render).join('');
  function extract() {
    return Array.from(document.querySelectorAll('article[data-testid="tweet"]')).flatMap(a=>{
      const time=a.querySelector('time[datetime]');
      const href=time?.closest('a')?.getAttribute('href');
      const m=/^\/([^/]+)\/status\/(\d+)/.exec(href||'');
      const text=render(a.querySelector('[data-testid="tweetText"]')).replace(/\s+/g,' ').trim();
      if(!m||!text)return [];
      const labels=Array.from(a.querySelectorAll('button[aria-label]')).map(e=>e.getAttribute('aria-label'));
      const label=regex=>labels.find(x=>regex.test(x));
      return [{tweet_id:m[2],username:m[1],url:'https://x.com'+href,text,
        created_at:time.getAttribute('datetime'),post_lang:a.querySelector('[data-testid="tweetText"]')?.getAttribute('lang'),
        n_reply:C.metric(label(/\bRepl/i)),n_repost:C.metric(label(/\brepost/i)),n_like:C.metric(label(/\bLikes?\./i)),
        metric_labels:labels,text_truncated:Array.from(a.querySelectorAll('button')).some(e=>/Show more|Tampilkan lebih banyak/.test(e.innerText))}];
    });
  }
  async function run({config:c,job,token}) {
    if(running)return;
    running=true;cancelled=false;
    const seen=new Set();let idle=0,loadingRounds=0,outside=0,status='stopped';
    try {
      while(!cancelled) {
        const main=document.querySelector('main');
        const input=document.querySelector('input[role="combobox"]');
        if(location.pathname.includes('/login')||location.pathname.includes('/i/flow')) {status='login_required';break;}
        if(input && input.value!==C.query(c,job)) {status='query_changed';break;}
        const records=extract();
        const body=main?.innerText||'';
        const alerts=Array.from(document.querySelectorAll('[role="alert"]')).map(e=>e.innerText).join(' ');
        if(/rate limit|too many requests|terlalu banyak permintaan/i.test(alerts)||
           (!records.length&&/Something went wrong|Try reloading|Terjadi kesalahan/i.test(body))) {status='platform_error';break;}
        if(!records.length&&/No results for|Tidak ada hasil/i.test(body)) {status='empty_search';break;}
        const loading=!!main?.querySelector('[role="progressbar"]');
        if(!records.length) {
          if(++loadingRounds>=10){status='loading_timeout';break;}
          await sleep(c.scrollDelayMs);continue;
        }
        loadingRounds=0;
        let fresh=0;
        for(const r of records)if(!seen.has(r.tweet_id)){seen.add(r.tweet_id);fresh++;}
        idle=fresh?0:idle+1;
        const valid=records.filter(r=>C.inJob(job,r.created_at));
        outside+=records.length-valid.length;
        const ack=await chrome.runtime.sendMessage({type:'BATCH',token,jobId:job.id,records:valid,
          progress:{seen:seen.size,scrollY:Math.round(window.scrollY),outsideWindow:outside}});
        if(!ack?.ok){status=ack?.reason||'storage_error';break;}
        if(ack.stop){status=ack.reason;break;}
        const bottom=window.scrollY+window.innerHeight>=document.documentElement.scrollHeight-100;
        if(idle>=c.idleRounds&&!loading){status=bottom?'exhausted_visible_results':'scroll_stalled_partial';break;}
        // Save the complete current DOM batch BEFORE scrolling: X virtualizes old posts.
        window.scrollBy({top:Math.max(500,window.innerHeight*1.7),behavior:'instant'});
        await sleep(c.scrollDelayMs+Math.random()*1500);
      }
    } catch(e) {status='collector_error';}
    finally {
      running=false;
      try{await chrome.runtime.sendMessage({type:'JOB_DONE',token,jobId:job.id,status,seen:seen.size,outsideWindow:outside});}catch{}
    }
  }
  chrome.runtime.onMessage.addListener((m,_s,respond)=>{
    if(m.type==='RUN'){respond({ok:true});void run(m);}
    if(m.type==='STOP'){cancelled=true;respond({ok:true});}
  });
  void chrome.runtime.sendMessage({type:'READY'}).catch(()=>{});
})();
