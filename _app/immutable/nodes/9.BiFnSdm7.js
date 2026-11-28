import{s as it,d as u,i as o,a as Oe,b as g,c as d,h as pt,e as G,f as De,g as me,j as c,k as P,l as Ve,m as lt,o as nt,n as ut,p as ot,q as be,r as mt,t as _t,u as ft}from"../chunks/scheduler.v3ijTZs9.js";import{S as dt,i as ct,d as k,t as h,a as f,c as Te,m as q,b as C,e as E,g as Se}from"../chunks/index.DybJngn3.js";import{D as We,e as ht,s as $t,Q as Re,p as vt,C as B,a as Ke,r as Xe,b as gt}from"../chunks/VennDiagram.svelte_svelte_type_style_lang.kF5V66Qb.js";import{w as yt}from"../chunks/entry._2xH9Zkd.js";import{h as se,p as bt}from"../chunks/setTrackProxy.DjIbdjlZ.js";import{p as wt}from"../chunks/stores.BCqDmflJ.js";import{B as Fe,Q as He}from"../chunks/BigValue.CLQVM3TY.js";import{B as kt}from"../chunks/BarChart.CSpocMPq.js";function qt(m){let s,a=y.title+"",t;return{c(){s=P("h1"),t=ft(a),this.h()},l(l){s=G(l,"H1",{class:!0});var n=mt(s);t=_t(n,a),n.forEach(u),this.h()},h(){g(s,"class","title")},m(l,n){o(l,s,n),Oe(s,t)},p:be,d(l){l&&u(s)}}}function Ct(m){return{c(){this.h()},l(s){this.h()},h(){document.title="Evidence"},m:be,p:be,d:be}}function Et(m){let s,a,t,l,n;return document.title=s=y.title,{c(){a=c(),t=P("meta"),l=c(),n=P("meta"),this.h()},l(i){a=d(i),t=G(i,"META",{property:!0,content:!0}),l=d(i),n=G(i,"META",{name:!0,content:!0}),this.h()},h(){var i,_;g(t,"property","og:title"),g(t,"content",((i=y.og)==null?void 0:i.title)??y.title),g(n,"name","twitter:title"),g(n,"content",((_=y.og)==null?void 0:_.title)??y.title)},m(i,_){o(i,a,_),o(i,t,_),o(i,l,_),o(i,n,_)},p(i,_){_&0&&s!==(s=y.title)&&(document.title=s)},d(i){i&&(u(a),u(t),u(l),u(n))}}}function Tt(m){var n,i;let s,a,t=(y.description||((n=y.og)==null?void 0:n.description))&&St(),l=((i=y.og)==null?void 0:i.image)&&Rt();return{c(){t&&t.c(),s=c(),l&&l.c(),a=De()},l(_){t&&t.l(_),s=d(_),l&&l.l(_),a=De()},m(_,b){t&&t.m(_,b),o(_,s,b),l&&l.m(_,b),o(_,a,b)},p(_,b){var T,F;(y.description||(T=y.og)!=null&&T.description)&&t.p(_,b),(F=y.og)!=null&&F.image&&l.p(_,b)},d(_){_&&(u(s),u(a)),t&&t.d(_),l&&l.d(_)}}}function St(m){let s,a,t,l,n;return{c(){s=P("meta"),a=c(),t=P("meta"),l=c(),n=P("meta"),this.h()},l(i){s=G(i,"META",{name:!0,content:!0}),a=d(i),t=G(i,"META",{property:!0,content:!0}),l=d(i),n=G(i,"META",{name:!0,content:!0}),this.h()},h(){var i,_,b;g(s,"name","description"),g(s,"content",y.description??((i=y.og)==null?void 0:i.description)),g(t,"property","og:description"),g(t,"content",((_=y.og)==null?void 0:_.description)??y.description),g(n,"name","twitter:description"),g(n,"content",((b=y.og)==null?void 0:b.description)??y.description)},m(i,_){o(i,s,_),o(i,a,_),o(i,t,_),o(i,l,_),o(i,n,_)},p:be,d(i){i&&(u(s),u(a),u(t),u(l),u(n))}}}function Rt(m){let s,a,t;return{c(){s=P("meta"),a=c(),t=P("meta"),this.h()},l(l){s=G(l,"META",{property:!0,content:!0}),a=d(l),t=G(l,"META",{name:!0,content:!0}),this.h()},h(){var l,n;g(s,"property","og:image"),g(s,"content",Ke((l=y.og)==null?void 0:l.image)),g(t,"name","twitter:image"),g(t,"content",Ke((n=y.og)==null?void 0:n.image))},m(l,n){o(l,s,n),o(l,a,n),o(l,t,n)},p:be,d(l){l&&(u(s),u(a),u(t))}}}function Ye(m){let s,a;return s=new He({props:{queryID:"lines",queryResult:m[0]}}),{c(){E(s.$$.fragment)},l(t){C(s.$$.fragment,t)},m(t,l){q(s,t,l),a=!0},p(t,l){const n={};l[0]&1&&(n.queryResult=t[0]),s.$set(n)},i(t){a||(f(s.$$.fragment,t),a=!0)},o(t){h(s.$$.fragment,t),a=!1},d(t){k(s,t)}}}function Ze(m){let s,a;return s=new He({props:{queryID:"by_supplier",queryResult:m[1]}}),{c(){E(s.$$.fragment)},l(t){C(s.$$.fragment,t)},m(t,l){q(s,t,l),a=!0},p(t,l){const n={};l[0]&2&&(n.queryResult=t[1]),s.$set(n)},i(t){a||(f(s.$$.fragment,t),a=!0)},o(t){h(s.$$.fragment,t),a=!1},d(t){k(s,t)}}}function et(m){let s,a;return s=new He({props:{queryID:"totals",queryResult:m[2]}}),{c(){E(s.$$.fragment)},l(t){C(s.$$.fragment,t)},m(t,l){q(s,t,l),a=!0},p(t,l){const n={};l[0]&4&&(n.queryResult=t[2]),s.$set(n)},i(t){a||(f(s.$$.fragment,t),a=!0)},o(t){h(s.$$.fragment,t),a=!1},d(t){k(s,t)}}}function tt(m){let s,a;return s=new He({props:{queryID:"ppv_quarter",queryResult:m[3]}}),{c(){E(s.$$.fragment)},l(t){C(s.$$.fragment,t)},m(t,l){q(s,t,l),a=!0},p(t,l){const n={};l[0]&8&&(n.queryResult=t[3]),s.$set(n)},i(t){a||(f(s.$$.fragment,t),a=!0)},o(t){h(s.$$.fragment,t),a=!1},d(t){k(s,t)}}}function rt(m){let s,a;return s=new He({props:{queryID:"outage",queryResult:m[4]}}),{c(){E(s.$$.fragment)},l(t){C(s.$$.fragment,t)},m(t,l){q(s,t,l),a=!0},p(t,l){const n={};l[0]&16&&(n.queryResult=t[4]),s.$set(n)},i(t){a||(f(s.$$.fragment,t),a=!0)},o(t){h(s.$$.fragment,t),a=!1},d(t){k(s,t)}}}function st(m){let s,a;return s=new He({props:{queryID:"outage_total",queryResult:m[5]}}),{c(){E(s.$$.fragment)},l(t){C(s.$$.fragment,t)},m(t,l){q(s,t,l),a=!0},p(t,l){const n={};l[0]&32&&(n.queryResult=t[5]),s.$set(n)},i(t){a||(f(s.$$.fragment,t),a=!0)},o(t){h(s.$$.fragment,t),a=!1},d(t){k(s,t)}}}function Ft(m){let s,a,t,l,n,i,_,b,T,F,w,S,R,H;return s=new B({props:{id:"supplier",title:"Supplier"}}),t=new B({props:{id:"supplier_status",title:"Status"}}),n=new B({props:{id:"spend_usd",title:"Spend",fmt:"usd0k"}}),_=new B({props:{id:"orders",title:"Orders"}}),T=new B({props:{id:"on_time_pct",title:"On time",fmt:"pct0",contentType:"colorscale"}}),w=new B({props:{id:"in_full_pct",title:"In full",fmt:"pct0",contentType:"colorscale"}}),R=new B({props:{id:"ppv_usd",title:"Price variance",fmt:"usd0k"}}),{c(){E(s.$$.fragment),a=c(),E(t.$$.fragment),l=c(),E(n.$$.fragment),i=c(),E(_.$$.fragment),b=c(),E(T.$$.fragment),F=c(),E(w.$$.fragment),S=c(),E(R.$$.fragment)},l(r){C(s.$$.fragment,r),a=d(r),C(t.$$.fragment,r),l=d(r),C(n.$$.fragment,r),i=d(r),C(_.$$.fragment,r),b=d(r),C(T.$$.fragment,r),F=d(r),C(w.$$.fragment,r),S=d(r),C(R.$$.fragment,r)},m(r,$){q(s,r,$),o(r,a,$),q(t,r,$),o(r,l,$),q(n,r,$),o(r,i,$),q(_,r,$),o(r,b,$),q(T,r,$),o(r,F,$),q(w,r,$),o(r,S,$),q(R,r,$),H=!0},p:be,i(r){H||(f(s.$$.fragment,r),f(t.$$.fragment,r),f(n.$$.fragment,r),f(_.$$.fragment,r),f(T.$$.fragment,r),f(w.$$.fragment,r),f(R.$$.fragment,r),H=!0)},o(r){h(s.$$.fragment,r),h(t.$$.fragment,r),h(n.$$.fragment,r),h(_.$$.fragment,r),h(T.$$.fragment,r),h(w.$$.fragment,r),h(R.$$.fragment,r),H=!1},d(r){r&&(u(a),u(l),u(i),u(b),u(F),u(S)),k(s,r),k(t,r),k(n,r),k(_,r),k(T,r),k(w,r),k(R,r)}}}function Ht(m){let s,a,t,l,n,i,_,b,T,F,w,S,R,H;return s=new B({props:{id:"order_ref",title:"PO"}}),t=new B({props:{id:"supplier",title:"Supplier"}}),n=new B({props:{id:"date_order",title:"Ordered",fmt:"mmm-d-yyyy"}}),_=new B({props:{id:"qty_received",title:"kg",fmt:"num0"}}),T=new B({props:{id:"price_unit",title:"Paid $/kg",fmt:"$0.000"}}),w=new B({props:{id:"preferred_price",title:"Mill's last $/kg",fmt:"$0.000"}}),R=new B({props:{id:"premium_usd",title:"Premium",fmt:"usd0"}}),{c(){E(s.$$.fragment),a=c(),E(t.$$.fragment),l=c(),E(n.$$.fragment),i=c(),E(_.$$.fragment),b=c(),E(T.$$.fragment),F=c(),E(w.$$.fragment),S=c(),E(R.$$.fragment)},l(r){C(s.$$.fragment,r),a=d(r),C(t.$$.fragment,r),l=d(r),C(n.$$.fragment,r),i=d(r),C(_.$$.fragment,r),b=d(r),C(T.$$.fragment,r),F=d(r),C(w.$$.fragment,r),S=d(r),C(R.$$.fragment,r)},m(r,$){q(s,r,$),o(r,a,$),q(t,r,$),o(r,l,$),q(n,r,$),o(r,i,$),q(_,r,$),o(r,b,$),q(T,r,$),o(r,F,$),q(w,r,$),o(r,S,$),q(R,r,$),H=!0},p:be,i(r){H||(f(s.$$.fragment,r),f(t.$$.fragment,r),f(n.$$.fragment,r),f(_.$$.fragment,r),f(T.$$.fragment,r),f(w.$$.fragment,r),f(R.$$.fragment,r),H=!0)},o(r){h(s.$$.fragment,r),h(t.$$.fragment,r),h(n.$$.fragment,r),h(_.$$.fragment,r),h(T.$$.fragment,r),h(w.$$.fragment,r),h(R.$$.fragment,r),H=!1},d(r){r&&(u(a),u(l),u(i),u(b),u(F),u(S)),k(s,r),k(t,r),k(n,r),k(_,r),k(T,r),k(w,r),k(R,r)}}}function Mt(m){let s,a,t,l,n,i,_,b,T,F,w,S,R=`What the plant buys, from whom, and how prices and suppliers performed. Seven
suppliers: four <strong class="markdown">preferred</strong> partners that win the business by default, and three
<strong class="markdown">approved</strong> backups.`,H,r,$,J,V,j,ae,W,_e,x,ie='<a href="#who-do-we-buy-from-and-do-they-deliver">Who do we buy from, and do they deliver?</a>',K,Q,fe,X,we=`The glucose mill carries most of the spend and misses about one delivery in ten. The
packaging converter is the cheapest bag supplier but the least reliable (about four in
five on time, some short shipments). The chemicals distributor costs more and is never
late. That trade-off is why it is the preferred partner rather than the cheaper broadline
distributor.`,Y,A,de='<a href="#are-we-paying-more-or-less-than-planned">Are we paying more or less than planned?</a>',ce,Z,ke=`Purchase price variance = (price paid − standard cost) × quantity received. Standard costs
are set each January from December's market prices, so variance shows how markets moved
during the year. Above zero = paid more than planned.`,ee,z,pe,te,qe=`In 2024 corn fell after the standard was set, so glucose came in under plan. In 2026
nitrogen chemicals rose all year with the fertilizer market (US producer price index),
and variance turned unfavorable.`,he,N,le='<a href="#what-did-the-august-2025-glucose-outage-cost">What did the August 2025 glucose outage cost?</a>',ne,re,Ce=`The preferred mill could not deliver for four weeks. Production never stopped: the buyer
placed emergency orders with the backup supplier, who delivered in a week at a premium.`,$e,v,Ee,ve,Ue,ge,Ie,ye,Ae=`Against the yearly standard these orders even look favorable, because corn had fallen
below the January standard. The real cost of the outage is the premium over what the
preferred mill was charging at the time.`,Le,ue=typeof y<"u"&&y.title&&y.hide_title!==!0&&qt();function at(e,p){return typeof y<"u"&&y.title?Et:Ct}let Me=at()(m),oe=typeof y=="object"&&Tt(),M=m[0]&&Ye(m),U=m[1]&&Ze(m),I=m[2]&&et(m),L=m[3]&&tt(m),O=m[4]&&rt(m),D=m[5]&&st(m);return r=new Fe({props:{data:m[2],value:"spend_usd",title:"Spend, Jan 2024 to Nov 2026",fmt:"usd1m"}}),J=new Fe({props:{data:m[2],value:"preferred_share",title:"Spend with preferred partners",fmt:"pct1"}}),j=new Fe({props:{data:m[2],value:"ppv_usd",title:"Price variance vs standard",fmt:"usd0k"}}),W=new Fe({props:{data:m[2],value:"otif_pct",title:"Supplier on time and in full",fmt:"pct1"}}),Q=new We({props:{data:m[1],rows:"10",$$slots:{default:[Ft]},$$scope:{ctx:m}}}),z=new kt({props:{data:m[3],x:"quarter",y:"ppv_usd",series:"material_group",type:"stacked",yFmt:"usd0k",title:"Purchase price variance by quarter",colorPalette:["#236aa4","#e8590c","#8dacbf"]}}),v=new Fe({props:{data:m[5],value:"premium_usd",title:"Premium paid to the backup",fmt:"usd0k"}}),ve=new Fe({props:{data:m[5],value:"kg",title:"Glucose bought in the outage (kg)",fmt:"num0"}}),ge=new We({props:{data:m[4],$$slots:{default:[Ht]},$$scope:{ctx:m}}}),{c(){ue&&ue.c(),s=c(),Me.c(),a=P("meta"),t=P("meta"),oe&&oe.c(),l=De(),n=c(),M&&M.c(),i=c(),U&&U.c(),_=c(),I&&I.c(),b=c(),L&&L.c(),T=c(),O&&O.c(),F=c(),D&&D.c(),w=c(),S=P("p"),S.innerHTML=R,H=c(),E(r.$$.fragment),$=c(),E(J.$$.fragment),V=c(),E(j.$$.fragment),ae=c(),E(W.$$.fragment),_e=c(),x=P("h2"),x.innerHTML=ie,K=c(),E(Q.$$.fragment),fe=c(),X=P("p"),X.textContent=we,Y=c(),A=P("h2"),A.innerHTML=de,ce=c(),Z=P("p"),Z.textContent=ke,ee=c(),E(z.$$.fragment),pe=c(),te=P("p"),te.textContent=qe,he=c(),N=P("h2"),N.innerHTML=le,ne=c(),re=P("p"),re.textContent=Ce,$e=c(),E(v.$$.fragment),Ee=c(),E(ve.$$.fragment),Ue=c(),E(ge.$$.fragment),Ie=c(),ye=P("p"),ye.textContent=Ae,this.h()},l(e){ue&&ue.l(e),s=d(e);const p=pt("svelte-2igo1p",document.head);Me.l(p),a=G(p,"META",{name:!0,content:!0}),t=G(p,"META",{name:!0,content:!0}),oe&&oe.l(p),l=De(),p.forEach(u),n=d(e),M&&M.l(e),i=d(e),U&&U.l(e),_=d(e),I&&I.l(e),b=d(e),L&&L.l(e),T=d(e),O&&O.l(e),F=d(e),D&&D.l(e),w=d(e),S=G(e,"P",{class:!0,"data-svelte-h":!0}),me(S)!=="svelte-z9xs20"&&(S.innerHTML=R),H=d(e),C(r.$$.fragment,e),$=d(e),C(J.$$.fragment,e),V=d(e),C(j.$$.fragment,e),ae=d(e),C(W.$$.fragment,e),_e=d(e),x=G(e,"H2",{class:!0,id:!0,"data-svelte-h":!0}),me(x)!=="svelte-vyv5z3"&&(x.innerHTML=ie),K=d(e),C(Q.$$.fragment,e),fe=d(e),X=G(e,"P",{class:!0,"data-svelte-h":!0}),me(X)!=="svelte-1xgez4g"&&(X.textContent=we),Y=d(e),A=G(e,"H2",{class:!0,id:!0,"data-svelte-h":!0}),me(A)!=="svelte-tp1tov"&&(A.innerHTML=de),ce=d(e),Z=G(e,"P",{class:!0,"data-svelte-h":!0}),me(Z)!=="svelte-kaxd0i"&&(Z.textContent=ke),ee=d(e),C(z.$$.fragment,e),pe=d(e),te=G(e,"P",{class:!0,"data-svelte-h":!0}),me(te)!=="svelte-1encx6a"&&(te.textContent=qe),he=d(e),N=G(e,"H2",{class:!0,id:!0,"data-svelte-h":!0}),me(N)!=="svelte-aidwjf"&&(N.innerHTML=le),ne=d(e),re=G(e,"P",{class:!0,"data-svelte-h":!0}),me(re)!=="svelte-9cw17a"&&(re.textContent=Ce),$e=d(e),C(v.$$.fragment,e),Ee=d(e),C(ve.$$.fragment,e),Ue=d(e),C(ge.$$.fragment,e),Ie=d(e),ye=G(e,"P",{class:!0,"data-svelte-h":!0}),me(ye)!=="svelte-z5edou"&&(ye.textContent=Ae),this.h()},h(){g(a,"name","twitter:card"),g(a,"content","summary_large_image"),g(t,"name","twitter:site"),g(t,"content","@evidence_dev"),g(S,"class","markdown"),g(x,"class","markdown"),g(x,"id","who-do-we-buy-from-and-do-they-deliver"),g(X,"class","markdown"),g(A,"class","markdown"),g(A,"id","are-we-paying-more-or-less-than-planned"),g(Z,"class","markdown"),g(te,"class","markdown"),g(N,"class","markdown"),g(N,"id","what-did-the-august-2025-glucose-outage-cost"),g(re,"class","markdown"),g(ye,"class","markdown")},m(e,p){ue&&ue.m(e,p),o(e,s,p),Me.m(document.head,null),Oe(document.head,a),Oe(document.head,t),oe&&oe.m(document.head,null),Oe(document.head,l),o(e,n,p),M&&M.m(e,p),o(e,i,p),U&&U.m(e,p),o(e,_,p),I&&I.m(e,p),o(e,b,p),L&&L.m(e,p),o(e,T,p),O&&O.m(e,p),o(e,F,p),D&&D.m(e,p),o(e,w,p),o(e,S,p),o(e,H,p),q(r,e,p),o(e,$,p),q(J,e,p),o(e,V,p),q(j,e,p),o(e,ae,p),q(W,e,p),o(e,_e,p),o(e,x,p),o(e,K,p),q(Q,e,p),o(e,fe,p),o(e,X,p),o(e,Y,p),o(e,A,p),o(e,ce,p),o(e,Z,p),o(e,ee,p),q(z,e,p),o(e,pe,p),o(e,te,p),o(e,he,p),o(e,N,p),o(e,ne,p),o(e,re,p),o(e,$e,p),q(v,e,p),o(e,Ee,p),q(ve,e,p),o(e,Ue,p),q(ge,e,p),o(e,Ie,p),o(e,ye,p),Le=!0},p(e,p){typeof y<"u"&&y.title&&y.hide_title!==!0&&ue.p(e,p),Me.p(e,p),typeof y=="object"&&oe.p(e,p),e[0]?M?(M.p(e,p),p[0]&1&&f(M,1)):(M=Ye(e),M.c(),f(M,1),M.m(i.parentNode,i)):M&&(Se(),h(M,1,1,()=>{M=null}),Te()),e[1]?U?(U.p(e,p),p[0]&2&&f(U,1)):(U=Ze(e),U.c(),f(U,1),U.m(_.parentNode,_)):U&&(Se(),h(U,1,1,()=>{U=null}),Te()),e[2]?I?(I.p(e,p),p[0]&4&&f(I,1)):(I=et(e),I.c(),f(I,1),I.m(b.parentNode,b)):I&&(Se(),h(I,1,1,()=>{I=null}),Te()),e[3]?L?(L.p(e,p),p[0]&8&&f(L,1)):(L=tt(e),L.c(),f(L,1),L.m(T.parentNode,T)):L&&(Se(),h(L,1,1,()=>{L=null}),Te()),e[4]?O?(O.p(e,p),p[0]&16&&f(O,1)):(O=rt(e),O.c(),f(O,1),O.m(F.parentNode,F)):O&&(Se(),h(O,1,1,()=>{O=null}),Te()),e[5]?D?(D.p(e,p),p[0]&32&&f(D,1)):(D=st(e),D.c(),f(D,1),D.m(w.parentNode,w)):D&&(Se(),h(D,1,1,()=>{D=null}),Te());const Ne={};p[0]&4&&(Ne.data=e[2]),r.$set(Ne);const je={};p[0]&4&&(je.data=e[2]),J.$set(je);const ze={};p[0]&4&&(ze.data=e[2]),j.$set(ze);const Qe={};p[0]&4&&(Qe.data=e[2]),W.$set(Qe);const Ge={};p[0]&2&&(Ge.data=e[1]),p[1]&131072&&(Ge.$$scope={dirty:p,ctx:e}),Q.$set(Ge);const Be={};p[0]&8&&(Be.data=e[3]),z.$set(Be);const xe={};p[0]&32&&(xe.data=e[5]),v.$set(xe);const Je={};p[0]&32&&(Je.data=e[5]),ve.$set(Je);const Pe={};p[0]&16&&(Pe.data=e[4]),p[1]&131072&&(Pe.$$scope={dirty:p,ctx:e}),ge.$set(Pe)},i(e){Le||(f(M),f(U),f(I),f(L),f(O),f(D),f(r.$$.fragment,e),f(J.$$.fragment,e),f(j.$$.fragment,e),f(W.$$.fragment,e),f(Q.$$.fragment,e),f(z.$$.fragment,e),f(v.$$.fragment,e),f(ve.$$.fragment,e),f(ge.$$.fragment,e),Le=!0)},o(e){h(M),h(U),h(I),h(L),h(O),h(D),h(r.$$.fragment,e),h(J.$$.fragment,e),h(j.$$.fragment,e),h(W.$$.fragment,e),h(Q.$$.fragment,e),h(z.$$.fragment,e),h(v.$$.fragment,e),h(ve.$$.fragment,e),h(ge.$$.fragment,e),Le=!1},d(e){e&&(u(s),u(n),u(i),u(_),u(b),u(T),u(F),u(w),u(S),u(H),u($),u(V),u(ae),u(_e),u(x),u(K),u(fe),u(X),u(Y),u(A),u(ce),u(Z),u(ee),u(pe),u(te),u(he),u(N),u(ne),u(re),u($e),u(Ee),u(Ue),u(Ie),u(ye)),ue&&ue.d(e),Me.d(e),u(a),u(t),oe&&oe.d(e),u(l),M&&M.d(e),U&&U.d(e),I&&I.d(e),L&&L.d(e),O&&O.d(e),D&&D.d(e),k(r,e),k(J,e),k(j,e),k(W,e),k(Q,e),k(z,e),k(v,e),k(ve,e),k(ge,e)}}}const y={title:"Purchasing"};function Ut(m,s,a){let t,l;Ve(m,wt,v=>a(32,t=v)),Ve(m,Xe,v=>a(38,l=v));let{data:n}=s,{data:i={},customFormattingSettings:_,__db:b,inputs:T}=n;lt(Xe,l="ab8e4f7292341d0da2bbb11dd2a9fe84",l);let F=ht(yt(T));nt(F.subscribe(v=>T=v)),ut(gt,{getCustomFormats:()=>_.customFormats||[]});const w=(v,Ee)=>bt(b.query,v,{query_name:Ee});$t(w),t.params,ot(()=>!0);let S={initialData:void 0,initialError:void 0},R=se`select * from pps.purchase_lines`,H="select * from pps.purchase_lines";i.lines_data&&(i.lines_data instanceof Error?S.initialError=i.lines_data:S.initialData=i.lines_data,i.lines_columns&&(S.knownColumns=i.lines_columns));let r,$=!1;const J=Re.createReactive({callback:v=>{a(0,r=v)},execFn:w},{id:"lines",...S});J(H,{noResolve:R,...S}),globalThis[Symbol.for("lines")]={get value(){return r}};let V={initialData:void 0,initialError:void 0},j=se`select supplier, supplier_status,
       sum(spend_usd)                         as spend_usd,
       count(distinct order_ref)              as orders,
       avg(case when on_time then 1.0 else 0 end) as on_time_pct,
       avg(case when in_full then 1.0 else 0 end) as in_full_pct,
       avg(case when on_time and in_full then 1.0 else 0 end) as otif_pct,
       sum(ppv_usd)                           as ppv_usd
from (select * from pps.purchase_lines) group by 1, 2 order by spend_usd desc`,ae=`select supplier, supplier_status,
       sum(spend_usd)                         as spend_usd,
       count(distinct order_ref)              as orders,
       avg(case when on_time then 1.0 else 0 end) as on_time_pct,
       avg(case when in_full then 1.0 else 0 end) as in_full_pct,
       avg(case when on_time and in_full then 1.0 else 0 end) as otif_pct,
       sum(ppv_usd)                           as ppv_usd
from (select * from pps.purchase_lines) group by 1, 2 order by spend_usd desc`;i.by_supplier_data&&(i.by_supplier_data instanceof Error?V.initialError=i.by_supplier_data:V.initialData=i.by_supplier_data,i.by_supplier_columns&&(V.knownColumns=i.by_supplier_columns));let W,_e=!1;const x=Re.createReactive({callback:v=>{a(1,W=v)},execFn:w},{id:"by_supplier",...V});x(ae,{noResolve:j,...V}),globalThis[Symbol.for("by_supplier")]={get value(){return W}};let ie={initialData:void 0,initialError:void 0},K=se`select sum(spend_usd) as spend_usd,
       sum(case when supplier_status = 'preferred' then spend_usd else 0 end) / sum(spend_usd) as preferred_share,
       sum(ppv_usd) as ppv_usd,
       avg(case when on_time and in_full then 1.0 else 0 end) as otif_pct
from (select * from pps.purchase_lines)`,Q=`select sum(spend_usd) as spend_usd,
       sum(case when supplier_status = 'preferred' then spend_usd else 0 end) / sum(spend_usd) as preferred_share,
       sum(ppv_usd) as ppv_usd,
       avg(case when on_time and in_full then 1.0 else 0 end) as otif_pct
from (select * from pps.purchase_lines)`;i.totals_data&&(i.totals_data instanceof Error?ie.initialError=i.totals_data:ie.initialData=i.totals_data,i.totals_columns&&(ie.knownColumns=i.totals_columns));let fe,X=!1;const we=Re.createReactive({callback:v=>{a(2,fe=v)},execFn:w},{id:"totals",...ie});we(Q,{noResolve:K,...ie}),globalThis[Symbol.for("totals")]={get value(){return fe}};let Y={initialData:void 0,initialError:void 0},A=se`select quarter,
       case when product_code = 'GLUCOSE' then 'Glucose (corn index)'
            when product_code in ('NH3', 'AMSULF') then 'Nitrogen chemicals'
            else 'Other materials' end as material_group,
       sum(ppv_usd) as ppv_usd
from (select * from pps.purchase_lines) group by 1, 2 order by 1`,de=`select quarter,
       case when product_code = 'GLUCOSE' then 'Glucose (corn index)'
            when product_code in ('NH3', 'AMSULF') then 'Nitrogen chemicals'
            else 'Other materials' end as material_group,
       sum(ppv_usd) as ppv_usd
from (select * from pps.purchase_lines) group by 1, 2 order by 1`;i.ppv_quarter_data&&(i.ppv_quarter_data instanceof Error?Y.initialError=i.ppv_quarter_data:Y.initialData=i.ppv_quarter_data,i.ppv_quarter_columns&&(Y.knownColumns=i.ppv_quarter_columns));let ce,Z=!1;const ke=Re.createReactive({callback:v=>{a(3,ce=v)},execFn:w},{id:"ppv_quarter",...Y});ke(de,{noResolve:A,...Y}),globalThis[Symbol.for("ppv_quarter")]={get value(){return ce}};let ee={initialData:void 0,initialError:void 0},z=se`-- what the outage cost: the backup's price vs the preferred mill's most recent price
with preferred as (
    select date_order, price_unit as preferred_price from (select * from pps.purchase_lines)
    where product_code = 'GLUCOSE' and supplier_status = 'preferred'
), em as (
    select * from (select * from pps.purchase_lines) where emergency
)
select em.order_ref, em.supplier, em.date_order, em.qty_received, em.price_unit, p.preferred_price,
       (em.price_unit - p.preferred_price) * em.qty_received as premium_usd,
       em.ppv_usd
from em asof join preferred p on em.date_order >= p.date_order
order by em.date_order`,pe=`-- what the outage cost: the backup's price vs the preferred mill's most recent price
with preferred as (
    select date_order, price_unit as preferred_price from (select * from pps.purchase_lines)
    where product_code = 'GLUCOSE' and supplier_status = 'preferred'
), em as (
    select * from (select * from pps.purchase_lines) where emergency
)
select em.order_ref, em.supplier, em.date_order, em.qty_received, em.price_unit, p.preferred_price,
       (em.price_unit - p.preferred_price) * em.qty_received as premium_usd,
       em.ppv_usd
from em asof join preferred p on em.date_order >= p.date_order
order by em.date_order`;i.outage_data&&(i.outage_data instanceof Error?ee.initialError=i.outage_data:ee.initialData=i.outage_data,i.outage_columns&&(ee.knownColumns=i.outage_columns));let te,qe=!1;const he=Re.createReactive({callback:v=>{a(4,te=v)},execFn:w},{id:"outage",...ee});he(pe,{noResolve:z,...ee}),globalThis[Symbol.for("outage")]={get value(){return te}};let N={initialData:void 0,initialError:void 0},le=se`select sum(premium_usd) as premium_usd, sum(qty_received) as kg from (-- what the outage cost: the backup's price vs the preferred mill's most recent price
with preferred as (
    select date_order, price_unit as preferred_price from (select * from pps.purchase_lines)
    where product_code = 'GLUCOSE' and supplier_status = 'preferred'
), em as (
    select * from (select * from pps.purchase_lines) where emergency
)
select em.order_ref, em.supplier, em.date_order, em.qty_received, em.price_unit, p.preferred_price,
       (em.price_unit - p.preferred_price) * em.qty_received as premium_usd,
       em.ppv_usd
from em asof join preferred p on em.date_order >= p.date_order
order by em.date_order)`,ne=`select sum(premium_usd) as premium_usd, sum(qty_received) as kg from (-- what the outage cost: the backup's price vs the preferred mill's most recent price
with preferred as (
    select date_order, price_unit as preferred_price from (select * from pps.purchase_lines)
    where product_code = 'GLUCOSE' and supplier_status = 'preferred'
), em as (
    select * from (select * from pps.purchase_lines) where emergency
)
select em.order_ref, em.supplier, em.date_order, em.qty_received, em.price_unit, p.preferred_price,
       (em.price_unit - p.preferred_price) * em.qty_received as premium_usd,
       em.ppv_usd
from em asof join preferred p on em.date_order >= p.date_order
order by em.date_order)`;i.outage_total_data&&(i.outage_total_data instanceof Error?N.initialError=i.outage_total_data:N.initialData=i.outage_total_data,i.outage_total_columns&&(N.knownColumns=i.outage_total_columns));let re,Ce=!1;const $e=Re.createReactive({callback:v=>{a(5,re=v)},execFn:w},{id:"outage_total",...N});return $e(ne,{noResolve:le,...N}),globalThis[Symbol.for("outage_total")]={get value(){return re}},m.$$set=v=>{"data"in v&&a(6,n=v.data)},m.$$.update=()=>{m.$$.dirty[0]&64&&a(7,{data:i={},customFormattingSettings:_,__db:b}=n,i),m.$$.dirty[0]&128&&vt.set(Object.keys(i).length>0),m.$$.dirty[1]&2&&t.params,m.$$.dirty[0]&3840&&(R||!$?R||(J(H,{noResolve:R,...S}),a(11,$=!0)):J(H,{noResolve:R})),m.$$.dirty[0]&61440&&(j||!_e?j||(x(ae,{noResolve:j,...V}),a(15,_e=!0)):x(ae,{noResolve:j})),m.$$.dirty[0]&983040&&(K||!X?K||(we(Q,{noResolve:K,...ie}),a(19,X=!0)):we(Q,{noResolve:K})),m.$$.dirty[0]&15728640&&(A||!Z?A||(ke(de,{noResolve:A,...Y}),a(23,Z=!0)):ke(de,{noResolve:A})),m.$$.dirty[0]&251658240&&(z||!qe?z||(he(pe,{noResolve:z,...ee}),a(27,qe=!0)):he(pe,{noResolve:z})),m.$$.dirty[0]&1879048192|m.$$.dirty[1]&1&&(le||!Ce?le||($e(ne,{noResolve:le,...N}),a(31,Ce=!0)):$e(ne,{noResolve:le}))},a(9,R=se`select * from pps.purchase_lines`),a(10,H="select * from pps.purchase_lines"),a(13,j=se`select supplier, supplier_status,
       sum(spend_usd)                         as spend_usd,
       count(distinct order_ref)              as orders,
       avg(case when on_time then 1.0 else 0 end) as on_time_pct,
       avg(case when in_full then 1.0 else 0 end) as in_full_pct,
       avg(case when on_time and in_full then 1.0 else 0 end) as otif_pct,
       sum(ppv_usd)                           as ppv_usd
from (select * from pps.purchase_lines) group by 1, 2 order by spend_usd desc`),a(14,ae=`select supplier, supplier_status,
       sum(spend_usd)                         as spend_usd,
       count(distinct order_ref)              as orders,
       avg(case when on_time then 1.0 else 0 end) as on_time_pct,
       avg(case when in_full then 1.0 else 0 end) as in_full_pct,
       avg(case when on_time and in_full then 1.0 else 0 end) as otif_pct,
       sum(ppv_usd)                           as ppv_usd
from (select * from pps.purchase_lines) group by 1, 2 order by spend_usd desc`),a(17,K=se`select sum(spend_usd) as spend_usd,
       sum(case when supplier_status = 'preferred' then spend_usd else 0 end) / sum(spend_usd) as preferred_share,
       sum(ppv_usd) as ppv_usd,
       avg(case when on_time and in_full then 1.0 else 0 end) as otif_pct
from (select * from pps.purchase_lines)`),a(18,Q=`select sum(spend_usd) as spend_usd,
       sum(case when supplier_status = 'preferred' then spend_usd else 0 end) / sum(spend_usd) as preferred_share,
       sum(ppv_usd) as ppv_usd,
       avg(case when on_time and in_full then 1.0 else 0 end) as otif_pct
from (select * from pps.purchase_lines)`),a(21,A=se`select quarter,
       case when product_code = 'GLUCOSE' then 'Glucose (corn index)'
            when product_code in ('NH3', 'AMSULF') then 'Nitrogen chemicals'
            else 'Other materials' end as material_group,
       sum(ppv_usd) as ppv_usd
from (select * from pps.purchase_lines) group by 1, 2 order by 1`),a(22,de=`select quarter,
       case when product_code = 'GLUCOSE' then 'Glucose (corn index)'
            when product_code in ('NH3', 'AMSULF') then 'Nitrogen chemicals'
            else 'Other materials' end as material_group,
       sum(ppv_usd) as ppv_usd
from (select * from pps.purchase_lines) group by 1, 2 order by 1`),a(25,z=se`-- what the outage cost: the backup's price vs the preferred mill's most recent price
with preferred as (
    select date_order, price_unit as preferred_price from (select * from pps.purchase_lines)
    where product_code = 'GLUCOSE' and supplier_status = 'preferred'
), em as (
    select * from (select * from pps.purchase_lines) where emergency
)
select em.order_ref, em.supplier, em.date_order, em.qty_received, em.price_unit, p.preferred_price,
       (em.price_unit - p.preferred_price) * em.qty_received as premium_usd,
       em.ppv_usd
from em asof join preferred p on em.date_order >= p.date_order
order by em.date_order`),a(26,pe=`-- what the outage cost: the backup's price vs the preferred mill's most recent price
with preferred as (
    select date_order, price_unit as preferred_price from (select * from pps.purchase_lines)
    where product_code = 'GLUCOSE' and supplier_status = 'preferred'
), em as (
    select * from (select * from pps.purchase_lines) where emergency
)
select em.order_ref, em.supplier, em.date_order, em.qty_received, em.price_unit, p.preferred_price,
       (em.price_unit - p.preferred_price) * em.qty_received as premium_usd,
       em.ppv_usd
from em asof join preferred p on em.date_order >= p.date_order
order by em.date_order`),a(29,le=se`select sum(premium_usd) as premium_usd, sum(qty_received) as kg from (-- what the outage cost: the backup's price vs the preferred mill's most recent price
with preferred as (
    select date_order, price_unit as preferred_price from (select * from pps.purchase_lines)
    where product_code = 'GLUCOSE' and supplier_status = 'preferred'
), em as (
    select * from (select * from pps.purchase_lines) where emergency
)
select em.order_ref, em.supplier, em.date_order, em.qty_received, em.price_unit, p.preferred_price,
       (em.price_unit - p.preferred_price) * em.qty_received as premium_usd,
       em.ppv_usd
from em asof join preferred p on em.date_order >= p.date_order
order by em.date_order)`),a(30,ne=`select sum(premium_usd) as premium_usd, sum(qty_received) as kg from (-- what the outage cost: the backup's price vs the preferred mill's most recent price
with preferred as (
    select date_order, price_unit as preferred_price from (select * from pps.purchase_lines)
    where product_code = 'GLUCOSE' and supplier_status = 'preferred'
), em as (
    select * from (select * from pps.purchase_lines) where emergency
)
select em.order_ref, em.supplier, em.date_order, em.qty_received, em.price_unit, p.preferred_price,
       (em.price_unit - p.preferred_price) * em.qty_received as premium_usd,
       em.ppv_usd
from em asof join preferred p on em.date_order >= p.date_order
order by em.date_order)`),[r,W,fe,ce,te,re,n,i,S,R,H,$,V,j,ae,_e,ie,K,Q,X,Y,A,de,Z,ee,z,pe,qe,N,le,ne,Ce,t]}class zt extends dt{constructor(s){super(),ct(this,s,Ut,Mt,it,{data:6},null,[-1,-1])}}export{zt as component};
