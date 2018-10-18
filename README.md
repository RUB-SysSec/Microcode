# x86 Microcode Framework and Example Programs

This repository contains the framework used during our work on reverse engineering the microcode of AMD K8 and K10 CPUs. It includes an assembler and disassembler as well as example programs implemented using these tools. We also provide our custom written minimal operating system that can rapidly apply and test microcode updates on AMD CPUs.

## Disclaimer

The here provided files originated from research and are meant to be used for research purposes only. They are compiled with only partial knowledge about the microarchitecture's internals and may contain bugs as well as unintended behavior. All files are provided as is without any warranties and support. We assume no responsibility or liability for the use of them.

## Background

The x86 instruction set is complex and contains many legacy instructions only kept for backward compatibility. Thus, rarely used or complex instructions are decoded in software, while performance critical instructions are handled by hardware decoders. Regardless of being decoded by hardware or software the instructions ultimately are translated to another instruction set named RISC86, which has a fixed instruction length and is suited for fast, superscalar processing. Besides software decoding microcode may be used to disable defective processor features and handle exceptions at the lowest level.

The content of this repository reflects the practical results of our research effort. Details are given in our papers:

[*Reverse Engineering x86 Processor Microcode*](http://syssec.rub.de/research/publications/microcode-reversing/) published in the proceedings of the [26th USENIX Security Symposium](https://www.usenix.org/conference/usenixsecurity17)

[*An Exploratory Analysis of Microcode as a Building Block for System Defenses*](https://www.syssec.rub.de/research/publications/constructive-microcode/) published in the proceedings of the [25th ACM Conference on Computer and Communications Security](https://www.sigsac.org/ccs/CCS2018/)

## Structure

The folder Usenix17 contains the results of our Usenix 2017 paper, most importantly the updates and triggers for our proof-of-concepts as well as an update driver allowing arbitrary updates to be loaded on a Linux system. Further details are given in the corresponding readme file.

Our minimal operating system is contained in the folder angry_os. For details on how to build and use this system see the readme file in that folder.

The framework we used during our work is found in the folder ucodeapi. For examples on how this API is used see the example scripts provided in this folder. The API is only tested under Python 2.

The folder "case studies" contains the case studies presented in our CSS 18 paper in RTL form.
