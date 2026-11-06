// 1コマずつ描いて ffmpeg に流し込み、MP4 を作る
const {chromium}=require('playwright');const {spawn}=require('child_process');
const [,,url,audio,out,fpsS,endS]=process.argv; const FPS=+fpsS, END=+endS, N=Math.round(END*FPS);
(async()=>{
 const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
 p.on('pageerror',e=>console.error('ERR',e.message));
 await p.goto(url);await p.evaluate(()=>window.__ready);
 const ff=spawn('ffmpeg',['-v','error','-y','-f','image2pipe','-framerate',String(FPS),'-c:v','mjpeg','-i','-','-i',audio,
   '-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',out],{stdio:['pipe','inherit','inherit']});
 const B=15; const t0=Date.now();
 for(let i=0;i<N;i+=B){
   const frames=await p.evaluate(([i,B,N,FPS])=>{const c=document.getElementById('c');const o=[];for(let k=i;k<Math.min(i+B,N);k++){__draw(k/FPS);o.push(c.toDataURL('image/jpeg',.93).split(',')[1]);}return o;},[i,B,N,FPS]);
   for(const f of frames){ if(!ff.stdin.write(Buffer.from(f,'base64'))) await new Promise(r=>ff.stdin.once('drain',r)); }
   if(i%(FPS*10)===0) console.log('frame',i,'/',N,((Date.now()-t0)/1000).toFixed(0)+'s');
 }
 ff.stdin.end(); await new Promise(r=>ff.on('close',r)); await b.close(); console.log('done',out,((Date.now()-t0)/1000).toFixed(0)+'s');
})();
