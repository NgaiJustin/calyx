#!/usr/bin/env python3

import calyx.builder as cb
from calyx import py_ast
from gen_array_component import NAME_SCHEME
from systolic_arg_parser import SystolicConfiguration
from calyx.utils import bits_needed

BITWIDTH = 32
INPUT_COMP_NAME = "input_comp"
OUTPUT_COMP_NAME = "output_comp"

#XXX(CALEB): copied from gen-systolic.py, should factor out the common code.
def create_mem_connections(
    main: cb.ComponentBuilder,
    component_builder: cb.ComponentBuilder,
    mem_name: str,
    mem_size: int,
    read_mem: bool,
):
    """
    Instantiates 1d memory named mem_name with idx widths of idx_width.
    Also connects the memory ports to `component_builder`
    If `read_mem` == True, then connects memory ports such that
    `component_builder` can read from memory.
    If `read_mem` == False, then connects memory ports such that
    `component_builder` can write to memory.
    """
    mem = main.mem_d1(
        mem_name,
        BITWIDTH,
        mem_size,
        bits_needed(mem_size),
        is_external=True,
    )
    input_port_names = ["addr0"] if read_mem else ["write_data", "write_en", "addr0"]
    output_port_names = ["read_data"] if read_mem else ["done"]
    return cb.build_connections(
        mem, component_builder, "", f"{mem_name}_", input_port_names, output_port_names
    )

def output_comp_params(comp: cb.ComponentBuilder, num_cols: int):
    """
    """
    cb.add_comp_params(
        comp,
        input_ports=[
            ("out_valid", 1),
            ("out_bits", 1),
        ],
        output_ports=[
          # Output comp should tell the systolic array when a given column
          # number is ready.
          ("out_ready", 1)],
    )
    cb.add_write_mem_params(
        comp, f"out_mem", data_width=BITWIDTH, addr_width=bits_needed(num_cols)
    )
    comp.output("finished_writing", 1)

def output_comp(prog: cb.Builder, num_cols: int):
    """
    """
    comp = prog.component(name=OUTPUT_COMP_NAME)
    output_comp_params(comp, num_cols=num_cols)
    idx_width = bits_needed(num_cols)
    idx_reg = comp.reg(idx_width, "idx_reg")
    incr_idx = comp.add(idx_width, "incr_idx")

    this = comp.this()
    finished_writing = (idx_reg.out == cb.ExprBuilder(
        py_ast.ConstantPort(idx_width, num_cols)
    ))
    should_write_mem = (~(finished_writing)) & this.out_valid

    with comp.continuous:
      # Tell systolic array that we're ready as long we're not finished.
      this.out_ready = finished_writing @ 0
      this.out_ready = ~finished_writing @ 1
      incr_idx.left = idx_reg.out
      incr_idx.right = 1
      # Increment index as we're writing to register.
      idx_reg.write_en = should_write_mem @ 1
      idx_reg.in_ = incr_idx.out
      # Write to memory.
      this.out_mem_in = this.out_bits
      this.out_mem_write_en = should_write_mem @ 1
      this.out_mem_addr0 = (~finished_writing) @ idx_reg.out

      this.finished_writing = finished_writing @ 1

def input_comp_params(comp: cb.ComponentBuilder, num_cols: int):
    cb.add_comp_params(
        comp,
        input_ports=[("in_ready",1)],
        output_ports=[
            ("in_valid",1),
            ("in_bits",1),
        ],
    )
    cb.add_read_mem_params(
        comp, f"in_mem", data_width=BITWIDTH, addr_width=bits_needed(num_cols)
    )
    comp.input("finished_sending", 1)

def input_comp(prog: cb.Builder, num_cols: int):
  """
  """
  comp = prog.component(name=INPUT_COMP_NAME)
  input_comp_params(comp, num_cols=num_cols)
  idx_width = bits_needed(num_cols)
  idx_reg = comp.reg(idx_width, "idx_reg")
  incr_idx = comp.add(idx_width, "incr_idx")

  this = comp.this()
  finished_sending = (idx_reg.out == (idx_reg.out == cb.ExprBuilder(
        py_ast.ConstantPort(idx_width, num_cols)
  )))
  should_send_next = (~finished_sending) & this.in_ready

  hi_signal = cb.ExprBuilder(py_ast.ConstantPort(1, 1))

  with comp.continuous:
    # Tell systolic array that we're ready as long we're not finished.
    this.in_valid = finished_sending @ 0
    this.in_valid = ~finished_sending @ 1
    incr_idx.left = idx_reg.out
    incr_idx.right = 1
    # Increment index as we're sending the data to input
    idx_reg.write_en = should_send_next @ 1
    idx_reg.in_ = incr_idx.out
    # Write to memory.
    this.in_mem_in = this.out_bits
    this.in_mem_write_en = should_send_next @ hi_signal
    this.out_mem_addr0 = (~finished_sending) @ idx_reg.out

    this.finished_sending = finished_sending @ 1

if __name__ == "__main__":
  systolic_config = SystolicConfiguration()
  systolic_config.parse_arguments()
  num_out_rows, num_out_cols = systolic_config.get_output_dimensions()
  prog = cb.Builder()
  input_comp(prog, num_cols=systolic_config.left_depth)
  output_comp(prog, num_out_cols)
  main = prog.component("main")
  hec_SA = main.cell(f"hec_SA", py_ast.CompInst("systolic_array", []))
  left_inputs = []
  for i in range(systolic_config.left_length):
    left_inputs.append(main.cell(f"left_input_comp_{i}", py_ast.CompInst(INPUT_COMP_NAME, [])))
  top_inputs = []
  for i in range(systolic_config.top_length):
    top_inputs.append(main.cell(f"top_input_comp_{i}", py_ast.CompInst(INPUT_COMP_NAME, [])))
  outputs = []
  for i in range(num_out_rows):
    outputs.append(main.cell(f"output_comp_{i}", py_ast.CompInst(OUTPUT_COMP_NAME, [])))

  cur_idx = 17
  handshake_connections = []
  memory_connections = []
  for i,top_input in enumerate(top_inputs):
    handshake_connections.append((top_input.in_ready, hec_SA.port(f"var{cur_idx}_ready")))
    handshake_connections.append((hec_SA.port(f"var{cur_idx}_valid"), top_input.in_valid))
    handshake_connections.append((hec_SA.port(f"var{cur_idx}_bits"), top_input.in_bits))
    memory_connections += create_mem_connections(main=main, component_builder=top_input, mem_name=f"t{i}", mem_size=systolic_config.top_depth, read_mem=True)
    cur_idx += 1

  for i,left_input in enumerate(left_inputs):
    handshake_connections.append((left_input.in_ready, hec_SA.port(f"var{cur_idx}_ready")))
    handshake_connections.append((hec_SA.port(f"var{cur_idx}_valid"), left_input.in_valid))
    handshake_connections.append((hec_SA.port(f"var{cur_idx}_bits"), left_input.in_bits))
    memory_connections += create_mem_connections(main=main, component_builder=left_input, mem_name=f"l{i}", mem_size=systolic_config.left_depth, read_mem=True)
    cur_idx += 1
  for i,output in enumerate(outputs):
    handshake_connections.append((hec_SA.port(f"var{cur_idx}_ready"), output.out_ready))
    handshake_connections.append((output.out_valid, hec_SA.port(f"var{cur_idx}_valid")))
    handshake_connections.append((output.out_bits, hec_SA.port(f"var{cur_idx}_bits")))
    memory_connections += create_mem_connections(main=main, component_builder=output, mem_name=f"out_mem_{i}", mem_size=num_out_cols, read_mem=False)
    cur_idx += 1

  with main.group("perform_computation") as g:
    for (lhs,rhs) in handshake_connections:
      g.asgn(lhs, rhs)
    for (lhs,rhs) in memory_connections:
      g.asgn(lhs, rhs)

  prog.program.emit()






