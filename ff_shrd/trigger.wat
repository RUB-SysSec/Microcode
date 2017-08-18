(module
  (func $i (import "imports" "imported_func") (param i32))
  (func $myfunc (param $l i32) (param $r i32) (result i32)
    get_local $l
    i64.extend_u/i32
    i64.const 32
    i64.shl
    get_local $r
    i64.extend_u/i32    
    i64.or
    i64.const 0x12
    i64.shr_u
    i32.wrap/i64
    i32.const 0x739090CC
    i32.add
  )
  (export "exported_func" (func $myfunc))
)
