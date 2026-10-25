const $=id=>document.getElementById(id);let loaded=false;
async function request(message){const r=await chrome.runtime.sendMessage(message);if(!r?.ok)throw Error(r?.error||'Operasi gagal');return r;}
async function refresh(){
  try{
    const {state:s,defaults}=await request({type:'STATUS'});
    if(!loaded){$('config').value=JSON.stringify(s?.config||defaults,null,2);loaded=true;}
    $('status').textContent=s?JSON.stringify({status:s.status,running:s.running,mode:s.mode,
      post_mentah_unik:s.total,per_fase:s.counts,pekerjaan_diperiksa:s.cursor,total_pekerjaan:s.jobs.length,
      pekerjaan_sekarang:s.current,post_pekerjaan_ini:s.jobCount,scroll_y:s.scrollY,
      tanggal_di_luar_kueri:s.outsideWindow,diperbarui:s.updatedAt,error:s.error},null,2):'Belum dimulai.';
    $('pilot').disabled=$('full').disabled=!!s?.running;
    $('resume').disabled=!s||!!s.running;
    $('stop').disabled=!s?.running;
  }catch(e){$('error').textContent=e.message;}
}
async function act(type,mode){$('error').textContent='';try{
  const config=JSON.parse($('config').value);globalThis.MagangHubCore.validate(config);
  await request({type,mode,config});await refresh();
}catch(e){$('error').textContent=e.message;}}
$('pilot').onclick=()=>act('START','pilot');$('full').onclick=()=>act('START','full');
$('resume').onclick=()=>act('RESUME');$('stop').onclick=()=>act('STOP');
$('export').onclick=async()=>{try{
  const r=await request({type:'EXPORT'});
  const url=URL.createObjectURL(new Blob([JSON.stringify(r.export)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='maganghub-x-'+new Date().toISOString().replaceAll(':','-')+'.json';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),10000);
}catch(e){$('error').textContent=e.message;}};
void refresh();setInterval(refresh,2000);
