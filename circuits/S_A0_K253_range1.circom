pragma circom 2.0.0;
include "../node_modules/circomlib/circuits/comparators.circom";
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

template HabsP(n){signal input x[n];signal output out;
 if(n<=16){component h=Poseidon(n);for(var i=0;i<n;i++){h.inputs[i]<==x[i];}out<==h.out;}
 else{var c=(n+15)\16;component ch[c];component up=HabsP(c);
  for(var j=0;j<c;j++){var w=(j==c-1)?(n-16*j):16;ch[j]=Poseidon(w);for(var i=0;i<w;i++){ch[j].inputs[i]<==x[16*j+i];}up.x[j]<==ch[j].out;}
  out<==up.out;}}

template Main(){signal input f[253];signal input p[11];signal input s[11];signal input root;signal input t;
 component l=HabsP(253); for(var i=0;i<253;i++){l.x[i]<==f[i];}
 component m=MerkleProof(11); m.leaf<==l.out; for(var i=0;i<11;i++){m.pathIndices[i]<==p[i];m.siblings[i]<==s[i];}
 m.root===root; component ge=GreaterEqThan(64); ge.in[0]<==f[0]; ge.in[1]<==t; ge.out===1;}
component main {public [root,t]} = Main();
