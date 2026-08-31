const fs=require("fs"), vm=require("vm");
const html=fs.readFileSync(process.argv[2],"utf8");
const js=html.match(/<script>([\s\S]*)<\/script>/)[1];

// データ部のみ切り出し(ASSETS〜EP_TITLES定義まで)
const start=js.indexOf("const ASSETS");
const endMark="let SC = EP1;";
const data=js.slice(start, js.indexOf(endMark))
  + "\n" + js.match(/const EP_ORDER=\[[^\]]*\];/)[0];
const ctx={};
vm.createContext(ctx);
vm.runInContext(data + "\n;globalThis.__X={ASSETS,EPISODES,EP_ORDER,EP_TITLES,YU,EL,N};", ctx);
const X=ctx.__X;

// エンジン側の解決マップ(v57のソースから機械的に抽出)
const pick=(re)=>{const m=js.match(re); if(!m) throw new Error("map not found: "+re); return m[1];};
const keysOf=(body)=>[...body.matchAll(/([A-Za-z_$][\w$]*)\s*:\s*ASSETS\.([A-Za-z_$][\w$]*)/g)].map(m=>[m[1],m[2]]);

const BG   = keysOf(pick(/const BGMAP=\{([\s\S]*?)\};/));
const SPR  = keysOf(pick(/const SPMAP=\{([\s\S]*?)\};/));
const BGM  = keysOf(pick(/const srcMap=\{([\s\S]*?)\};/));
const YU   = keysOf(pick(/const M=\{([\s\S]*?)\};/));

const A=X.ASSETS;
const err=[], warn=[];

// 0) マップが指すASSETSキーの存在
for(const [label,list] of [["BGMAP",BG],["SPMAP",SPR],["srcMap",BGM],["yuAvatar",YU]])
  for(const [k,a] of list)
    if(!(a in A)) err.push(`${label}: '${k}' -> ASSETS.${a} が存在しない`);

const bgOK=new Set(BG.map(x=>x[0])).add("none");
const sprOK=new Set(SPR.map(x=>x[0])).add("none");
const bgmOK=new Set(BGM.map(x=>x[0]));
const yuOK=new Set(YU.map(x=>x[0]));

const EPISODES=X.EPISODES, ORDER=X.EP_ORDER, TITLES=X.EP_TITLES;

// 1) EP_ORDER / EPISODES / EP_TITLES の三者整合
for(const k of ORDER){
  if(!(k in EPISODES)) err.push(`EP_ORDER '${k}' に対応する EPISODES が無い`);
  if(!(k in TITLES))   err.push(`EP_ORDER '${k}' に対応する EP_TITLES が無い`);
}
for(const k of Object.keys(EPISODES)) if(!ORDER.includes(k)) err.push(`EPISODES '${k}' が EP_ORDER に無い`);
for(const k of Object.keys(TITLES))   if(!ORDER.includes(k)) err.push(`EP_TITLES '${k}' が EP_ORDER に無い`);

// 2) 各話:素材参照・ラベル/ジャンプ整合・終端
let cmds=0, texts=0, chars=0, choices=0;
for(const ep of ORDER){
  const sc=EPISODES[ep]; if(!sc){continue;}
  const labels=new Set(), jumps=[];
  sc.forEach((c,i)=>{
    cmds++;
    const at=`[${ep}#${i}]`;
    if(c.bg  !==undefined && !bgOK.has(c.bg))   err.push(`${at} bg:"${c.bg}" が BGMAP に無い`);
    if(c.spr !==undefined && !sprOK.has(c.spr)) err.push(`${at} spr:"${c.spr}" が SPMAP に無い`);
    if(c.bgm !==undefined && !bgmOK.has(c.bgm)) err.push(`${at} bgm:"${c.bgm}" が srcMap に無い`);
    if(c.yu  !==undefined && !yuOK.has(c.yu))   err.push(`${at} yu:"${c.yu}" が アバターMap に無い`);
    if(c.yu !==undefined && c.n!==X.YU)       warn.push(`${at} yu指定だが話者がユウジでない(表示されない)`);
    if(c.label!==undefined){ if(labels.has(c.label)) err.push(`${at} label '${c.label}' が重複`); labels.add(c.label); }
    if(c.jump!==undefined) jumps.push([at,c.jump]);
    if(c.choice) { choices++; c.choice.forEach(o=>{ if(o.jump) jumps.push([at+"(choice)",o.jump]); }); }
    if(c.t){ texts++; chars+=c.t.length; }
  });
  for(const [at,j] of jumps) if(!labels.has(j)) err.push(`${at} jump先 '${j}' のラベルが無い`);
  const last=sc[sc.length-1];
  if(!(last.ed||last.fin)) err.push(`[${ep}] 末尾が ed/fin で終わっていない`);
}

// 3) ifFlag が参照するフラグが、どこかの choice で立つか
const setFlags=new Set();
for(const ep of ORDER) (EPISODES[ep]||[]).forEach(c=>{
  if(c.choice) c.choice.forEach(o=>{ if(o.flag) setFlags.add(o.flag); });
  if(c.flag) setFlags.add(c.flag);
});
for(const ep of ORDER) (EPISODES[ep]||[]).forEach((c,i)=>{
  if(c.ifFlag && !setFlags.has(c.ifFlag)) err.push(`[${ep}#${i}] ifFlag '${c.ifFlag}' を立てる選択肢が存在しない`);
});

// 4) 未注入素材(プレースホルダ)
const ph=Object.keys(A).filter(k=>typeof A[k]==="string" && A[k].startsWith("__"));

console.log(`話数: ${ORDER.length} / コマンド: ${cmds} / テキスト行: ${texts} / 本文: ${chars}字 / 選択肢: ${choices}`);
if(ph.length) console.log(`未注入素材(${ph.length}): ${ph.join(", ")}`);
if(warn.length){ console.log("\n--- WARN ---"); warn.forEach(w=>console.log("  "+w)); }
if(err.length){ console.log("\n--- ERROR ---"); err.forEach(e=>console.log("  "+e)); console.log(`\nNG: ${err.length}件`); process.exit(1); }
console.log("\n参照整合 OK");
