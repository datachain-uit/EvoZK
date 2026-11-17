pragma circom 2.0.0;
include "../node_modules/circomlib/circuits/poseidon.circom";
include "../node_modules/circomlib/circuits/comparators.circom";
include "../node_modules/circomlib/circuits/bitify.circom";

template Sel(){signal input in[2];signal input s;signal output out[2];
 s*(s-1)===0;
 out[0] <== (in[1]-in[0])*s+in[0]; out[1] <== (in[0]-in[1])*s+in[1];}

template H2(){signal input a;signal input b;signal output o;component h=Poseidon(2);h.inputs[0]<==a;h.inputs[1]<==b;o<==h.out;}
template Habs(n){signal input x[n];signal output o;
 if(n<=16){component h=Poseidon(n);for(var i=0;i<n;i++){h.inputs[i]<==x[i];}o<==h.out;}
 else{var c=(n+15)\16;component ch[c];component top=Poseidon(c);
  for(var j=0;j<c;j++){var w=(j==c-1)?(n-16*j):16;ch[j]=Poseidon(w);for(var i=0;i<w;i++){ch[j].inputs[i]<==x[16*j+i];}top.inputs[j]<==ch[j].out;}
  o<==top.out;}}

template MP(){signal input leaf;signal input p[11];signal input s[11];signal output root;
 signal h[12];h[0]<==leaf;component sl[11];component hs[11];
 for(var i=0;i<11;i++){sl[i]=Sel();sl[i].in[0]<==h[i];sl[i].in[1]<==s[i];sl[i].s<==p[i];
  hs[i]=H2();hs[i].a<==sl[i].out[0];hs[i].b<==sl[i].out[1];h[i+1]<==hs[i].o;}
 root<==h[11];}
template Main(){signal input f[64];signal input p[11];signal input s[11];signal input root;signal input t;
 component l=Habs(64);for(var i=0;i<64;i++){l.x[i]<==f[i];}
 component m=MP();m.leaf<==l.o;for(var i=0;i<11;i++){m.p[i]<==p[i];m.s[i]<==s[i];} m.root===root;
 signal x0; x0<==f[0]; component ge=GreaterEqThan(64); ge.in[0]<==x0; ge.in[1]<==t; ge.out===1;}
component main {public [root,t]} = Main();
