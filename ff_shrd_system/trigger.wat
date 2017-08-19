(module
  (func $i (import "imports" "imported_func") (param i32))
  (import "imports" "mem" (memory 1))
  (func $myfunc (param $l i32) (param $r i32) (result i32)
    i32.const 0x0
    i64.load
    i64.const 0x12
    ;; this emits the shrd instruction
    i64.shr_u
    i32.wrap/i64
    ;; mov [ecx], esi
    ;; jmp 5
    i32.const 0x05EB3189
    i32.add
    ;; add to different variables to prevent the adds from being optimized into one
    i32.const 0x4
    i32.load
    ;; mov [edx], edi; int 0x80
    i32.const 0x80CD3A89
    ;; consume all temporary variables on the stack to prevent them from being optimized out
    i32.add
    i32.add
  )
  (export "exported_func" (func $myfunc))
)
