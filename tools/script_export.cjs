// 台本だけを書き出す(画像・音・演出を除いた、地の文と台詞と選択肢)
// 使い方: node tools/script_export.cjs crc/index.html > out.md
const fs=require("fs"), vm=require("vm");
const html=fs.readFileSync(process.argv[2],"utf8");
const js=html.match(/<script>([\s\S]*)<\/script>/)[1];
const data=js.slice(js.indexOf("const ASSETS"), js.indexOf("let SC = EP1;"))
  + "\n" + js.match(/const EP_ORDER=\[[^\]]*\];/)[0];
const ctx={}; vm.createContext(ctx);
vm.runInContext(data+"\n;globalThis.__X={EPISODES,EP_ORDER,EP_TITLES,N};", ctx);
const X=ctx.__X, build=(html.match(/name="build" content="([^"]+)"/)||[])[1];
const out=[];
out.push("# Cyber Rose Crimson 台本(全16話)","",
 `ゲーム本編(${build})から、地の文・台詞・選択肢だけを書き出したもの。画像・音楽・演出の指定は省いている。`,
 "原作・企画・音楽・ビジュアル shou.5150 / シナリオ shou.5150 × Claude","",
 "読み方:地の文はそのまま。台詞は「名前:「…」」。【選択肢】のあとの〈 〉は、その選択肢を選んだときだけ読む部分。","");
const q=x=>/^[「(]/.test(x)?x:"「"+x+"」";
const flagName={};
for(const ep of X.EP_ORDER) for(const c of X.EPISODES[ep]) if(c.choice) for(const o of c.choice) if(o.flag) flagName[o.flag]=o.label;
for(const ep of X.EP_ORDER){
  const sc=X.EPISODES[ep], t=X.EP_TITLES[ep]||["",""];
  out.push("---","",`## ${t[0]} ${t[1]}`,"");
  const labelName={};
  for(const c of sc) if(c.choice) for(const o of c.choice) labelName[o.jump]=o.label;
  let chars=0, inBranch=false;
  for(const c of sc){
    if(c.curtain) out.push("",`〔${c.curtain.replace(/^──/,"")}〕`,"");
    else if(c.curtain==="") out.push("");
    if(c.label!==undefined && labelName[c.label]){ out.push("",`〈${q(labelName[c.label])}を選んだ場合〉`); inBranch=true; }
    else if(c.label!==undefined && inBranch){ out.push("","〈ここから共通〉"); inBranch=false; }
    if(c.ifFlag) out.push("",`〈前に${q(flagName[c.ifFlag]||c.ifFlag)}を選んでいた場合は、ここで別の流れになる〉`);
    if(c.choice) out.push("",`【選択肢】${c.choice.map(o=>q(o.label)).join(" / ")}`,"");
    if(c.t!==undefined){ chars+=c.t.length;
      out.push(c.n && c.n!==X.N ? `${c.n}:${c.t}` : c.t); }
  }
  out.push("",`(${chars.toLocaleString()}字)`,"");
}
process.stdout.write(out.join("\n").replace(/\n{3,}/g,"\n\n"));
