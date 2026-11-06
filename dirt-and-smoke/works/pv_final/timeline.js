// DIRT AND SMOKE — PV（姉妹版・約3分）のタイムライン
// 画面も音も、すべてここに書いた秒数で動く。秒は「動画の頭からの秒」。
// 音の組み立て（mix.py）も、同じ秒数を使っている。秒を変えたら mix.py も合わせること。

(function(){
const BG=[], TXT=[], CUT=[], FLOOD=[], FLASH=[], ASH=[];
const bg=(t,img,o={})=>BG.push({t,img,filt:o.filt||'',fade:o.fade??1.6,snap:!!o.snap,kb:o.kb??true});
const txt=(t0,t1,lines,o={})=>TXT.push({t0,t1,lines,pos:o.pos||'low',out:o.out??.6,size:o.size||1});
const L=(s,mode='n',at=0,sp=.075,o={})=>({s,mode,at,sp,fast:!!o.fast,ghost:o.ghost||null,seed:o.seed||0,small:!!o.small});
const cut=(t,d,img)=>CUT.push({t,d,img});
const burst=(t,list)=>{ for(const [img,d] of list){ cut(t,d,img); t+=d; } return t; };

/* ---------------- A：姉妹の記憶（子守唄） ---------------- */
ASH.push([0,74.6],[116,171.5]);
txt(1.0,6.4,[L('灰と煙の中で、私《白》は目を覚ました。','n',0,.07)],{pos:'center'});
bg(6.6,'girl_lab',{filt:'cold',fade:2.6});
txt(8.2,13.0,[L('縫い目を数える。','n',0,.08),L('二十三本。','n',2.1,.11)]);
bg(13.4,'mirror1b',{filt:'cold',fade:1.2});
bg(16.6,'mirror1a',{filt:'cold',snap:true});           // 鏡の中の少女が、先に微笑む
bg(19.2,'mirror1b',{filt:'cold',snap:true});
bg(20.6,'kitchen',{fade:2.2});
txt(22.2,27.2,[L('「わたしの、かわいい子」','n',0,.1)]);
bg(27.6,'singing',{fade:1.8});
txt(28.6,34.0,[L('知らないはずの歌を、','n',0,.075),L('私《赤》は覚えていた。','n',1.6,.075)]);
bg(34.4,'record',{filt:'cold',fade:1.4});
txt(35.4,44.0,[L('左手　洗濯女　二十六歳','n',0,.06),L('右眼　不明','n',1.4,.06),
               L('心臓　','n',2.6,.06,{ghost:[{t:40.0,t1:44.0,s:'心臓　私《青》',mode:'n'}]})]);
bg(44.4,'gloves',{filt:'dark',fade:1.8});
txt(45.6,50.4,[L('「ずっと、一緒にいようね」','n',0,.1)]);

/* ---------------- B：イタイ ---------------- */
txt(51.0,55.5,[L('溶けて曖昧になる意識の中で','n',0,.09)],{pos:'center'});
txt(56.5,60.5,[L('お姉ちゃんも…痛いよね？','r',0,.095),L('ね？','r',2.0,.08)],{pos:'center'});
// 勝手に進む反復
txt(61.0,62.84,[L('痛いよね？','r',0,0,{fast:true}),L('痛いよね？','b',.7,0,{fast:true}),L('痛いよね？','r',1.32,0,{fast:true})],{pos:'center',out:0});
txt(62.84,64.34,[L('痛いよね？','b',0,0,{fast:true}),L('痛い？','r',.42,0,{fast:true}),L('ね？','m',.8,0,{fast:true})],{pos:'center',out:0});
{ // イタイ×7：一行に足されていく
  const ts=[0,.26,.498,.714,.908,1.08,1.23]; const s='イタイ'.repeat(7);
  txt(64.34,66.6,[L(s,'mr',0,0,{fast:true,seed:7})],{pos:'center',out:0});
  TXT[TXT.length-1].lines[0].reveal=ts;   // 3文字ずつ足していく時刻
}
txt(68.2,74.6,[L('いたい？','n',0,.14),L('いたい？','n',2.1,.14),L('ね？','w',4.0,.08)],{pos:'center',out:0});
bg(0,'none',{snap:true});                               // 冒頭は黒
bg(74.6,'none',{snap:true});                            // 絵も音も、一瞬で消える
FLOOD.push({t0:75.5,t1:78.7,n:760,center:false});       // 笑いが画面を埋め尽くす
txt(81.0,83.3,[L('ねえ？','r',0,.16)],{pos:'center',out:0});
FLOOD.push({t0:83.3,t1:84.1,n:6,center:true});
txt(87.1,92.3,[L('居たい？','b',0,.15),L('未だ居たい？','r',1.5,.15),L('ね？','m',3.4,.08)],{pos:'center',out:0});
txt(92.3,96.1,[L('イタイ？','mr',0,0,{fast:true,seed:3}),
               L('イタイ？','mr',1.02,0,{fast:true,seed:4,ghost:[{t:93.84,t1:93.91,s:'遺体？',mode:'w'}]}),
               L('イタイ？','mr',2.11,0,{fast:true,seed:5,ghost:[{t:94.93,t1:95.0,s:'異体？',mode:'w'}]})],{pos:'center',out:0});
txt(96.1,99.5,[L('痛い？','r',0,.12),L('居たい？','b',1.1,.12)],{pos:'center',out:0});
txt(103.5,108.2,[L('ずーと…一緒…','w',0,.21)],{pos:'center'});
txt(110.2,116.0,[L('汚れた《r:私:ワタシタチ》が','w',0,.0,{}),L('（ワタシタチ…）','n',2.6,.09,{small:true})],{pos:'center',out:0});

/* ---------------- C：主題歌（最後のサビ〜終わり） ---------------- */
// 曲は動画の 116.0 秒に、曲の 213.5 秒から入る。曲の秒 s は 動画の 116.0+(s-213.5)
const S=s=>116.0+(s-213.5);
let e=burst(116.0,[['mouth',.2],['nm_smoke',.18],['needle',.18],['eyes_red',.16],['cloth_after',.15],['prev2',.13],['nm_lying',.12],['eyes',.1],['prev5',.08],['eyes_red',.08]]);
bg(e,'mirror_back',{fade:.6});
cut(S(217.6),.08,'prev3');
bg(S(220.0),'empty_mirror',{fade:1.0});
txt(S(220.6),S(224.0),[L('「あなたは、誰？」','n',0,.1)]);
bg(S(224.3),'mirror8a',{snap:true});
bg(S(226.6),'mirror8b',{snap:true});
cut(S(227.6),.07,'eyes_red');
txt(S(228.6),S(236.5),[L('心の闇が','n',0,.12),L('本当の私《紫》','n',1.2,.14)],{pos:'center',size:1.15});
bg(S(236.0),'none',{fade:1.2});
bg(S(238.0),'ending_new',{fade:3.5});
txt(S(246.0),S(259.0),[L('DIRT AND SMOKE','n',0,0),L('総監督・音楽　shouyama','n',1.0,0,{small:true}),L('ビジュアル　ChatGPT','n',1.6,0,{small:true}),L('シナリオ　Claude','n',2.2,0,{small:true})],{pos:'credit',out:2.0});
bg(S(264.5),'none',{fade:3.5});
txt(175.0,181.5,[L('おやすみ。','n',0,.2)],{pos:'center',out:1.5});

BG.sort((a,b)=>a.t-b.t);
window.TL={BG,TXT,CUT,FLOOD,FLASH,ASH,END:183.0};
})();
