# x86 Microcode Samples

This directory contains a collection of x86 CPU microcode samples in binary and rtl form. The samples are compiled from scratch and specifically work with AMD's K10 processor family.

## Disclaimer

The here provided files originated from research and are meant to be used for research purposes only. They are compiled with only partial knowledge about the microarchitecture's internals and may contain bugs as well as unintended behavior. All files are provided as is without any warranties and support. We assume no responsibility or liability for the use of them.


## Background

The x86 instruction set is complex and contains many legacy instructions only kept for backward compatibility. Thus, rarely used or complex instructions are decoded in software, while performance critical instructions are handled by hardware decoders. Regardless of being decoded by hardware or software the instructions ultimately are translated to another instruction set named RISC86, which has a fixed instruction length and is suited for fast, superscalar processing. Besides software decoding microcode may be used to disable defective processor features and handle exceptions at the lowest level.

The content of this directory reflects the practical results of our research effort. Details are given in our paper [*Reverse Engineering x86 Processor Microcode*](http://syssec.rub.de/research/publications/microcode-reversing/) published in the proceedings of the [26th USENIX Security Symposium](https://www.usenix.org/conference/usenixsecurity17).

From the abstract:
>Microcode is an abstraction layer on top of the physical components of a CPU and present in most general-purpose CPUs today. In addition to facilitate complex and vast instruction sets, it also provides an update mechanism that allows CPUs to be patched in-place without requiring any special hardware. While it is well-known that CPUs are regularly updated with this mechanism, very little is known about its inner workings given that microcode and the update mechanism are proprietary and have not been throughly analyzed yet.
>
> In this paper, we reverse engineer the microcode semantics and inner workings of its update mechanism of conventional COTS CPUs on the example of AMD’s K8 and K10 microarchitectures. Furthermore, we demonstrate how to develop custom microcode updates. We describe the microcode semantics and additionally present a set of microprograms that demonstrate the possibilities offered by this technology. To this end, our microprograms range from CPU-assisted instrumentation to microcoded Trojans even reachable from within a web browser enabling remote code execution and cryptographic implementation attacks.

## Structure
```
.
├── ff_div
├── ff_shrd
├── ff_shrd_system
├── updatedriver
└── updates
    ├── *.bin
    └── *.rtl
```
The ff_div, ff_shrd and ff_shrd_system folders contain JavaScript code triggering microcode backdoors. The triggers use Asm.js and WebAssembly respectively. They work together with the microcode updates to gain arbitrary code execution without leveraging a memory error. The microcode updates implementing proof of concept Trojans, cryptographic bug attacks, timing side channels and dynamic instrumentations reside in the update folder.

## RTL

We use a custom RTL to represent the microprograms as readable text. This RTL is similar to Intel x86 assembly and instructions with names equal to those in x86 perform the same functions. The destination operand is written first, memory accesses are denoted with square brackets. The size of the destination operand determines the size of the operation. An important difference is the ability to use three operands in contrast to most x86 instructions only using one or two. In this case the first operand is still the destination, the second and third operands are the sources. Important, special opcodes are jcc - conditionally branch to the given triad and writePC - set the (x86) instruction pointer to the given value. Mnemonics can optionally be suffixed by certain flags that allow specifying additional options for the emitted instructions.

Register names are the same as for the x86 GPR if the register has a counterpart in x86. Internal microcode registers are denoted as a number starting with t and ending in the size of the operand (b, w, d and q for byte, word, double word and quad word). Special registers are pc(d), which contains the address of the next x86 instruction to be decoded and the regmd4-regmd6 registers, denoting placeholders filled by the substitution engine.

Additionally annotations allow for other options that do not apply to a single instruction. These annotations start with a ".". Examples are .sw_next - emit a "next" sequence word, .sw_branch ADDR - branch to the given triad and .sw_complete - exit instruction decoding and continue at the next x86 instruction.

The assembler also automatically applies some constraints. After three operations, a .sw_next is automatically inserted and certain operations that must be used at a specific position are automatically placed there using padding.

## Sample Microprogram

Given here is a sample microprogram that is meant to replace the original logic of the x86 instruction *cmpxchg*. This can be accomplished by setting a match register to address *0xb1a* and placing the microprogram at the corresponding offset in the microcode update (triad 0 for match register 0). At first the microprogram recreates the original semantics of the instruction to preserve its behavior. The substitution registers *regmd4* and *regmd6* get replaced with opcode operands at runtime. Then the microprogram checks for a trigger condition. In this case it compares *esi* to *0x42f00d*. Finally, it conditionally executes the payload, which in this case is incrementing the x86 register *edi*. It should be noted that the microprograms may contain loops and arbitrary logic as long as it meets the space requirements.

```javascript
.start 0x0

// emulate semantics of cmpxchg
jcc False, 0x1
sub t1d, eax, regmd4
jcc EZF, 0x1

mov eax, regmd4
mov eax, eax
jcc True, 0x1

mov regmd4, regmd6
mov eax, eax
mov eax, eax

// load magic constant
mov t1d, 0x0042
sll t1d, 16
add t1d, 0xf00d

// compare and execute payload conditionally
jcc False, 0x1
sub t1d, t1d, esi
jcc nEZF, 0x1

// payload
add edi, 0x1
mov eax, eax
mov eax, eax

// provides branch target
mov eax, eax
mov eax, eax
mov eax, eax

// end instruction decoding
.sw_complete
```

## Update driver

We also provide a patch file that patches the Linux kernel's microcode update driver to force a given update to be loaded. This driver or a similar change is needed to allow loading of non-matching microcode updates. For details see the folder "updatedriver".