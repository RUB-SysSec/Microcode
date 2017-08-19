# Updatedriver

This folder contains a patch file that patches the Linux kernel (based on 4.12.4-1). It changes the default microcode update driver to check for the presence of the file "/lib/firmware/amd-ucode/myupdate.bin" and if found apply it without any checking. This means it applies the update regardless of matching CPUID or patch level. While this allows testing of any update, this also posses a risk, because the CPU might be loaded with an incompatible update.
