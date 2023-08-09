# pylint: disable=import-error
import calyx.builder as cb
import calyx.builder_util as util


def insert_incr_helper(prog):
    """Inserts the component `incr_helper` into the program.

    It has no inputs. It has one ref register called `value`.
    It increments `value`.
    """
    incr_helper: cb.ComponentBuilder = prog.component("incr_helper")
    value = incr_helper.reg("value", 32, is_ref=True)
    incr_value = util.insert_incr(incr_helper, value, "incr_value")
    incr_helper.control += [incr_value]
    return incr_helper


def insert_incr(prog):
    """Inserts a the component `incr` into the program.

    It has no inputs. It has one ref register called `value`.
    It increments `value` by invoking the component `incr_helper`.
    """
    incr: cb.ComponentBuilder = prog.component("incr")
    value = incr.reg("value", 32, is_ref=True)
    helper = incr.cell("incr_helper", insert_incr_helper(prog))
    incr.control += [cb.invoke(helper, ref_value=value)]
    return incr


def insert_main(prog):
    """Inserts the component `main` into the program.

    It has no inputs. It creates a register and increments it using `incr`.
    """
    main: cb.ComponentBuilder = prog.component("main")
    incr = main.cell("incr", insert_incr(prog))
    value = main.reg("value", 32)
    main.control += [cb.invoke(incr, ref_value=value)]


def build():
    """Top-level function to build the program."""
    prog = cb.Builder()
    insert_main(prog)
    return prog.program


if __name__ == "__main__":
    build().emit()
