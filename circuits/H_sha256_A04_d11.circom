pragma circom 2.0.0;
include "../node_modules/circomlib/circuits/sha256/sha256.circom";
include "../node_modules/circomlib/circuits/bitify.circom";
include "../node_modules/circomlib/circuits/comparators.circom";

template Sel(){signal input in[2];signal input s;signal output out[2];
 s*(s-1)===0;
 out[0] <== (in[1]-in[0])*s+in[0]; out[1] <== (in[0]-in[1])*s+in[1];}

template Habs(n){signal input x[n];signal output o;component nb[n];component s=Sha256(256*n);
 for(var i=0;i<n;i++){nb[i]=Num2Bits(254);nb[i].in<==x[i];
  for(var k=0;k<256;k++){ if(k<2){s.in[256*i+k]<==0;} else {s.in[256*i+k]<==nb[i].out[255-k];} }}
 component pk=Bits2Num(253);for(var k=0;k<253;k++){pk.in[k]<==s.out[255-k];}o<==pk.out;}
template H2(){signal input a;signal input b;signal output o;component h=Habs(2);h.x[0]<==a;h.x[1]<==b;o<==h.o;}

template MP(){signal input leaf;signal input p[11];signal input s[11];signal output root;
 signal h[12];h[0]<==leaf;component sl[11];component hs[11];
 for(var i=0;i<11;i++){sl[i]=Sel();sl[i].in[0]<==h[i];sl[i].in[1]<==s[i];sl[i].s<==p[i];
  hs[i]=H2();hs[i].a<==sl[i].out[0];hs[i].b<==sl[i].out[1];h[i+1]<==hs[i].o;}
 root<==h[11];}
template Main(){signal input f[4];signal input p[11];signal input s[11];signal input root;signal input t;
 component l=Habs(4);for(var i=0;i<4;i++){l.x[i]<==f[i];}
 component m=MP();m.leaf<==l.o;for(var i=0;i<11;i++){m.p[i]<==p[i];m.s[i]<==s[i];} m.root===root;
 signal x0; x0<==f[0]; component ge=GreaterEqThan(64); ge.in[0]<==x0; ge.in[1]<==t; ge.out===1;}
component main {public [root,t]} = Main();
