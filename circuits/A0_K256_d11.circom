pragma circom 2.0.0;
include "../node_modules/circomlib/circuits/poseidon.circom";
// Template to select left/right based on selector
template Selector() {
    signal input in[2];  // [left, right]
    signal input s;      // selector (0 or 1)
    signal output out[2];

    // Constrain the selector to a single bit.
    // Without this, s ranges over the whole field. Since the sibling is also a
    // prover-chosen witness, the two Poseidon inputs at this level would then be
    // unconstrained, detaching the proof from the credential leaf: the circuit
    // would prove knowledge of a hash chain ending at root rather than knowledge
    // of a credential recorded in the registry.
    s * (s - 1) === 0;

    // s = 0: out = [in[0], in[1]]
    // s = 1: out = [in[1], in[0]]
    out[0] <== (in[1] - in[0]) * s + in[0];
    out[1] <== (in[0] - in[1]) * s + in[1];
}
// Template to verify Merkle proof
template MerkleProof(levels) {
    signal input leaf;
    signal input pathIndices[levels];
    signal input siblings[levels];
    signal output root;

    // Compute root from leaf and proof
    signal computedHash[levels + 1];
    computedHash[0] <== leaf;

    // Declare all components upfront
    component selectors[levels];
    component hashers[levels];
    
    // Initialize components
    for (var i = 0; i < levels; i++) {
        selectors[i] = Selector();
        hashers[i] = Poseidon(2);
    }

    // Walk from leaf up to root
    for (var i = 0; i < levels; i++) {
        // Order left/right based on pathIndex
        selectors[i].in[0] <== computedHash[i];
        selectors[i].in[1] <== siblings[i];
        selectors[i].s <== pathIndices[i];

        // Hash the left-right pair
        hashers[i].inputs[0] <== selectors[i].out[0];
        hashers[i].inputs[1] <== selectors[i].out[1];
        
        // Store hash result for the next level
        computedHash[i + 1] <== hashers[i].out;
    }

    // Root is the final hash
    root <== computedHash[levels];
}
template Leaf(){signal input f[256];signal output out;component c[16];component top=Poseidon(16);
 c[0]=Poseidon(16); for(var i=0;i<16;i++){c[0].inputs[i]<==f[0+i];} top.inputs[0]<==c[0].out;
 c[1]=Poseidon(16); for(var i=0;i<16;i++){c[1].inputs[i]<==f[16+i];} top.inputs[1]<==c[1].out;
 c[2]=Poseidon(16); for(var i=0;i<16;i++){c[2].inputs[i]<==f[32+i];} top.inputs[2]<==c[2].out;
 c[3]=Poseidon(16); for(var i=0;i<16;i++){c[3].inputs[i]<==f[48+i];} top.inputs[3]<==c[3].out;
 c[4]=Poseidon(16); for(var i=0;i<16;i++){c[4].inputs[i]<==f[64+i];} top.inputs[4]<==c[4].out;
 c[5]=Poseidon(16); for(var i=0;i<16;i++){c[5].inputs[i]<==f[80+i];} top.inputs[5]<==c[5].out;
 c[6]=Poseidon(16); for(var i=0;i<16;i++){c[6].inputs[i]<==f[96+i];} top.inputs[6]<==c[6].out;
 c[7]=Poseidon(16); for(var i=0;i<16;i++){c[7].inputs[i]<==f[112+i];} top.inputs[7]<==c[7].out;
 c[8]=Poseidon(16); for(var i=0;i<16;i++){c[8].inputs[i]<==f[128+i];} top.inputs[8]<==c[8].out;
 c[9]=Poseidon(16); for(var i=0;i<16;i++){c[9].inputs[i]<==f[144+i];} top.inputs[9]<==c[9].out;
 c[10]=Poseidon(16); for(var i=0;i<16;i++){c[10].inputs[i]<==f[160+i];} top.inputs[10]<==c[10].out;
 c[11]=Poseidon(16); for(var i=0;i<16;i++){c[11].inputs[i]<==f[176+i];} top.inputs[11]<==c[11].out;
 c[12]=Poseidon(16); for(var i=0;i<16;i++){c[12].inputs[i]<==f[192+i];} top.inputs[12]<==c[12].out;
 c[13]=Poseidon(16); for(var i=0;i<16;i++){c[13].inputs[i]<==f[208+i];} top.inputs[13]<==c[13].out;
 c[14]=Poseidon(16); for(var i=0;i<16;i++){c[14].inputs[i]<==f[224+i];} top.inputs[14]<==c[14].out;
 c[15]=Poseidon(16); for(var i=0;i<16;i++){c[15].inputs[i]<==f[240+i];} top.inputs[15]<==c[15].out;
 out<==top.out;}
template Main(){signal input f[256];signal input p[11];signal input s[11];signal input root;
 component l=Leaf(); for(var i=0;i<256;i++){l.f[i]<==f[i];}
 component m=MerkleProof(11); m.leaf<==l.out; for(var i=0;i<11;i++){m.pathIndices[i]<==p[i];m.siblings[i]<==s[i];}
 m.root===root;}
component main {public [root]} = Main();
