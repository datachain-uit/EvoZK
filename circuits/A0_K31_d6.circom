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
template Leaf(){signal input f[31];signal output out;component c[2];component top=Poseidon(2);
 c[0]=Poseidon(16); for(var i=0;i<16;i++){c[0].inputs[i]<==f[0+i];} top.inputs[0]<==c[0].out;
 c[1]=Poseidon(15); for(var i=0;i<15;i++){c[1].inputs[i]<==f[16+i];} top.inputs[1]<==c[1].out;
 out<==top.out;}
template Main(){signal input f[31];signal input p[6];signal input s[6];signal input root;
 component l=Leaf(); for(var i=0;i<31;i++){l.f[i]<==f[i];}
 component m=MerkleProof(6); m.leaf<==l.out; for(var i=0;i<6;i++){m.pathIndices[i]<==p[i];m.siblings[i]<==s[i];}
 m.root===root;}
component main {public [root]} = Main();
