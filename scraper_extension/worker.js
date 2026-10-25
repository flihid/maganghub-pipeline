import './core.js';
const C=globalThis.MagangHubCore;
const DB='maganghub-collector-v1';
const dbReady=new Promise((resolve,reject)=>{
  const r=indexedDB.open(DB,1);
  r.onupgradeneeded=()=>{
    r.result.createObjectStore('posts',{keyPath:'tweet_id'});
    r.result.createObjectStore('sightings',{keyPath:'key'});
  };
  r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);
});
async function allPosts(){const db=await dbReady;return new Promise((resolve,reject)=>{
  const r=db.transaction('posts').objectStore('posts').getAll();r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);
});}
const state=async()=>(await chrome.storage.local.get('state')).state;
const save=s=>chrome.storage.local.set({state:s});
let queue=Promise.resolve();
function serial(fn){const next=queue.then(fn,fn);queue=next.catch(()=>{});return next;}
async function notifyTab(s,message){if(s?.tabId)try{return await chrome.tabs.sendMessage(s.tabId,message);}catch{}return null;}
async function dispatch(tabId){
  const s=await state();
  if(!s?.running||s.tabId!==tabId||!s.current)return;
  await notifyTab(s,{type:'RUN',config:s.config,job:s.current,token:s.token});
}
async function nextJob(){
  const s=await state();if(!s?.running)return;
  const skipped=j=>s.mode==='pilot'&&(s.counts[j.fase]||0)>=s.config.pilotPerPhase;
  while(s.cursor<s.jobs.length&&skipped(s.jobs[s.cursor]))s.cursor++;
  if(s.cursor>=s.jobs.length||s.total>=s.config.maxRaw){
    s.running=false;s.status=s.total>=s.config.maxRaw?'raw_limit_partial':'job_list_finished';s.current=null;await save(s);return;
  }
  s.current=s.jobs[s.cursor];s.token=crypto.randomUUID();s.seen=0;s.outsideWindow=0;
  const db=await dbReady;
  s.jobCount=await new Promise((resolve,reject)=>{
    const prefix=s.current.id+'|';const r=db.transaction('sightings').objectStore('sightings').count(IDBKeyRange.bound(prefix,prefix+'\uffff'));
    r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);
  });
  s.status='opening_search';s.updatedAt=new Date().toISOString();await save(s);
  await chrome.alarms.create('watch-job',{when:Date.now()+90000});
  try{
    const url=C.url(s.config,s.current);
    if(s.tabId){try{await chrome.tabs.update(s.tabId,{url,active:false});return;}catch{}}
    const tab=await chrome.tabs.create({url,active:true});s.tabId=tab.id;await save(s);
  }catch(e){s.running=false;s.status='browser_error';s.error=String(e);await save(s);}
}
async function start(mode,config){
  const existing=await state();if(existing?.running)throw Error('Pengambilan masih berjalan; hentikan dulu sebelum memulai baru');
  C.validate(config);
  const posts=await allPosts();const counts={};
  for(const r of posts){const p=C.phaseOf(config,r.created_at);if(p)counts[p]=(counts[p]||0)+1;}
  const s={config,mode,running:true,status:'starting',jobs:C.jobs(config),cursor:0,current:null,
    counts,total:posts.length,logs:[],createdAt:new Date().toISOString()};
  await save(s);await nextJob();return {ok:true};
}
async function resume(){
  const s=await state();if(!s)throw Error('Belum ada pengambilan untuk dilanjutkan');
  s.running=true;s.error=null;await save(s);await nextJob();return {ok:true};
}
async function stop(){
  const s=await state();if(!s)return {ok:true};
  s.running=false;s.status='stopped_by_user';await save(s);await chrome.alarms.clear('next-job');
  await notifyTab(s,{type:'STOP'});return {ok:true};
}
async function storeBatch(m,sender){
  const s=await state();
  if(!s?.running||sender.tab?.id!==s.tabId||m.token!==s.token||m.jobId!==s.current?.id)
    return {ok:false,reason:'inactive_job'};
  const db=await dbReady;
  // Transactions commit posts and per-job sightings together before acknowledgement.
  const result=await new Promise((resolve,reject)=>{
    const tx=db.transaction(['posts','sightings'],'readwrite');
    const posts=tx.objectStore('posts'),sights=tx.objectStore('sightings');
    let added=0,jobAdded=0;const counts={...s.counts};let total=s.total,jobCount=s.jobCount;
    for(const input of new Map((m.records||[]).map(r=>[r.tweet_id,r])).values()){
      if(!/^\d+$/.test(input.tweet_id||'')||!input.text||!C.inJob(s.current,input.created_at))continue;
      const phase=C.phaseOf(s.config,input.created_at);if(!phase)continue;
      const key=s.current.id+'|'+input.tweet_id;const q=sights.get(key);
      q.onsuccess=()=>{
        if(q.result||jobCount>=s.config.maxPerDay)return;
        sights.put({key});jobAdded++;jobCount++;
        const get=posts.get(input.tweet_id);
        get.onsuccess=()=>{
          if(get.result||total>=s.config.maxRaw||(s.mode==='pilot'&&(counts[phase]||0)>=s.config.pilotPerPhase))return;
          posts.put({...input,fase:phase,kueri:s.config.query,language_filter:s.config.language,
            since:s.current.since,until:s.current.until,scraped_at:new Date().toISOString(),collector:'local_extension_v1'});
          added++;total++;counts[phase]=(counts[phase]||0)+1;
        };
      };
    }
    tx.oncomplete=()=>resolve({added,jobAdded,counts,total,jobCount});tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);
  });
  Object.assign(s,result,{status:'collecting',seen:m.progress?.seen||0,scrollY:m.progress?.scrollY||0,
    outsideWindow:m.progress?.outsideWindow||0,updatedAt:new Date().toISOString()});await save(s);
  let reason=null;
  if(s.total>=s.config.maxRaw)reason='raw_limit_partial';
  else if(s.mode==='pilot'&&(s.counts[s.current.fase]||0)>=s.config.pilotPerPhase)reason='pilot_phase_quota_partial';
  else if(s.jobCount>=s.config.maxPerDay)reason='day_cap_partial';
  return {ok:true,added:result.added,total:s.total,stop:!!reason,reason};
}
async function jobDone(m,sender){
  const s=await state();if(!s?.running||sender.tab?.id!==s.tabId||m.token!==s.token||m.jobId!==s.current?.id)return {ok:true};
  s.logs.push({...s.current,status:m.status,seen:m.seen,saved:s.jobCount,outsideWindow:m.outsideWindow,
    finishedAt:new Date().toISOString(),language_filter:s.config.language,kueri:s.config.query});
  await chrome.alarms.clear('watch-job');
  const blocked=['login_required','platform_error','collector_error','storage_error','query_changed','scroll_stalled_partial','loading_timeout','inactive_job'];
  if(blocked.includes(m.status)) {s.running=false;s.status=m.status;await save(s);return {ok:true};}
  if(m.status==='raw_limit_partial'){s.running=false;s.status=m.status;await save(s);return {ok:true};}
  s.cursor++;s.current=null;s.status='waiting_between_queries';s.nextAt=Date.now()+s.config.queryDelayMs+Math.random()*10000;
  await save(s);await chrome.alarms.create('next-job',{when:s.nextAt});return {ok:true};
}
chrome.runtime.onMessage.addListener((m,sender,respond)=>{
  if(m.type==='STATUS') {state().then(s=>respond({ok:true,state:s,defaults:C.defaults})).catch(e=>respond({ok:false,error:String(e)}));return true;}
  const handle=async()=>{
    if(m.type==='START')return start(m.mode,m.config);
    if(m.type==='RESUME')return resume();
    if(m.type==='STOP')return stop();
    if(m.type==='BATCH')return storeBatch(m,sender);
    if(m.type==='JOB_DONE')return jobDone(m,sender);
    if(m.type==='READY'){await dispatch(sender.tab?.id);return {ok:true};}
    if(m.type==='EXPORT')return {ok:true,export:{schema:'maganghub-x-export-v1',exportedAt:new Date().toISOString(),state:await state(),posts:await allPosts()}};
    return {ok:false,error:'Unknown message'};
  };
  serial(handle).then(respond,e=>respond({ok:false,error:String(e)}));return true;
});
chrome.tabs.onUpdated.addListener((tabId,info)=>{if(info.status==='complete')void dispatch(tabId);});
chrome.tabs.onRemoved.addListener(tabId=>{void serial(async()=>{const s=await state();if(s?.running&&s.tabId===tabId){s.running=false;s.status='collection_tab_closed';await save(s);}});});
chrome.alarms.onAlarm.addListener(a=>{
  if(a.name==='next-job')void serial(nextJob);
  if(a.name==='watch-job')void serial(async()=>{
    const s=await state();if(s?.running&&['opening_search','waiting_for_results'].includes(s.status)){
      s.running=false;s.status='page_not_ready';await save(s);await notifyTab(s,{type:'STOP'});
    }
  });
});
chrome.runtime.onStartup.addListener(()=>{void serial(async()=>{const s=await state();if(s?.running)await nextJob();});});
chrome.action.onClicked.addListener(()=>{void chrome.tabs.create({url:chrome.runtime.getURL('panel.html')});});
