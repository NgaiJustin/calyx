// Inspired by this blog post: http://thume.ca/2019/04/18/writing-a-compiler-in-rust/

use crate::context::Context;
use crate::errors;
use crate::lang::pretty_print::PrettyPrint;
use crate::lang::{ast::*, component::Component};

pub enum Action {
    /// Continue AST traversal
    Continue,
    /// Stop AST traversal
    Stop,
    /// Change the current ast node. Implies ending
    /// the traversal for this branch of the AST
    Change(Control),
}

impl Action {
    /// Monadic helper function that sequences actions
    /// that return a VisResult.
    /// If `self` is `Continue` or `Change`, return the result of running `f`.
    /// Pass `Stop` through
    fn and_then<F>(self, mut other: F) -> VisResult
    where
        F: FnMut() -> VisResult,
    {
        match self {
            Action::Continue => other(),
            x => Ok(x),
        }
    }

    /// Applies the Change action if `self` is a Change action.
    /// Otherwise passes the action through unchanged
    fn apply_change(self, con: &mut Control) -> VisResult {
        match self {
            Action::Change(c) => {
                *con = c;
                Ok(Action::Continue)
            }
            x => Ok(x),
        }
    }
}

pub type VisResult = Result<Action, errors::Error>;

/// The `Visitor` trait parameterized on an `Error` type.
/// For each node `x` in the Ast, there are the functions `start_x`
/// and `finish_x`. The start functions are called at the beginning
/// of the traversal for each node, and the finish functions are called
/// at the end of the traversal for each node. You can use the finish
/// functions to wrap error with more information.
pub trait Visitor {
    fn name(&self) -> String;

    fn do_pass_default(context: &Context) -> Result<Self, errors::Error>
    where
        Self: Default + Sized,
    {
        let mut visitor = Self::default();
        visitor.do_pass(&context)?;
        Ok(visitor)
    }

    fn do_pass(&mut self, context: &Context) -> Result<(), errors::Error>
    where
        Self: Sized,
    {
        context.definitions_map(|_id, mut comp| {
            let _ = self
                .start(&mut comp, context)?
                .and_then(|| {
                    // clone component control so that we can visit the control and provide
                    // mutable access to the component
                    let mut control = comp.control.clone();
                    control.visit(self, &mut comp, context)?;
                    // replace component control with the control we visited
                    comp.control = control;
                    Ok(Action::Continue)
                })?
                .and_then(|| self.finish(&mut comp, context))?;
            Ok(())
        })?;

        // Display intermediate futil program after running the pass.
        if context.debug_mode {
            println!("=============== {} ==============", self.name());
            context.pretty_print();
            println!("================================================");
        }

        Ok(())
    }

    fn start(&mut self, _comp: &mut Component, _c: &Context) -> VisResult {
        Ok(Action::Continue)
    }

    fn finish(&mut self, _comp: &mut Component, _c: &Context) -> VisResult {
        Ok(Action::Continue)
    }

    fn start_seq(
        &mut self,
        _s: &mut Seq,
        _comp: &mut Component,
        _c: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn finish_seq(
        &mut self,
        _s: &mut Seq,
        _comp: &mut Component,
        _c: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn start_par(
        &mut self,
        _s: &mut Par,
        _comp: &mut Component,
        _c: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn finish_par(
        &mut self,
        _s: &mut Par,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn start_if(
        &mut self,
        _s: &mut If,
        _comp: &mut Component,
        _c: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn finish_if(
        &mut self,
        _s: &mut If,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn start_ifen(
        &mut self,
        _s: &mut Ifen,
        _comp: &mut Component,
        _c: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn finish_ifen(
        &mut self,
        _s: &mut Ifen,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn start_while(
        &mut self,
        _s: &mut While,
        _comp: &mut Component,
        _c: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn finish_while(
        &mut self,
        _s: &mut While,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn start_print(
        &mut self,
        _s: &mut Print,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn finish_print(
        &mut self,
        _s: &mut Print,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn start_enable(
        &mut self,
        _s: &mut Enable,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn finish_enable(
        &mut self,
        _s: &mut Enable,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn start_disable(
        &mut self,
        _s: &mut Disable,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn finish_disable(
        &mut self,
        _s: &mut Disable,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn start_empty(
        &mut self,
        _s: &mut Empty,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }

    fn finish_empty(
        &mut self,
        _s: &mut Empty,
        _comp: &mut Component,
        _x: &Context,
    ) -> VisResult {
        Ok(Action::Continue)
    }
}

/** `Visitable` describes types that can be visited by things
implementing `Visitor`. This performs a recursive walk of the tree.
It calls `Visitor::start_*` on the way down, and `Visitor::finish_*`
on the way up. */
pub trait Visitable {
    fn visit(
        &mut self,
        visitor: &mut dyn Visitor,
        component: &mut Component,
        context: &Context,
    ) -> VisResult;
}

// Blanket impl for Vectors of Visitables
impl<V: Visitable> Visitable for Vec<V> {
    fn visit(
        &mut self,
        visitor: &mut dyn Visitor,
        component: &mut Component,
        context: &Context,
    ) -> VisResult {
        for t in self {
            match t.visit(visitor, component, context)? {
                Action::Continue | Action::Change(_) => continue,
                Action::Stop => return Ok(Action::Stop),
            };
        }
        Ok(Action::Continue)
    }
}

impl Visitable for Control {
    fn visit(
        &mut self,
        visitor: &mut dyn Visitor,
        component: &mut Component,
        context: &Context,
    ) -> VisResult {
        match self {
            Control::Seq { data } => visitor
                .start_seq(data, component, context)?
                .and_then(|| data.stmts.visit(visitor, component, context))?
                .and_then(|| visitor.finish_seq(data, component, context))?,
            Control::Par { data } => visitor
                .start_par(data, component, context)?
                .and_then(|| data.stmts.visit(visitor, component, context))?
                .and_then(|| visitor.finish_par(data, component, context))?,
            Control::If { data } => visitor
                .start_if(data, component, context)?
                .and_then(|| data.tbranch.visit(visitor, component, context))?
                .and_then(|| data.fbranch.visit(visitor, component, context))?
                .and_then(|| visitor.finish_if(data, component, context))?,
            Control::Ifen { data } => visitor
                .start_ifen(data, component, context)?
                .and_then(|| data.tbranch.visit(visitor, component, context))?
                .and_then(|| data.fbranch.visit(visitor, component, context))?
                .and_then(|| visitor.finish_ifen(data, component, context))?,
            Control::While { data } => visitor
                .start_while(data, component, context)?
                .and_then(|| data.body.visit(visitor, component, context))?
                .and_then(|| visitor.finish_while(data, component, context))?,
            Control::Print { data } => visitor
                .start_print(data, component, context)?
                .and_then(|| visitor.finish_print(data, component, context))?,
            Control::Enable { data } => visitor
                .start_enable(data, component, context)?
                .and_then(|| visitor.finish_enable(data, component, context))?,
            Control::Disable { data } => {
                visitor.start_disable(data, component, context)?.and_then(
                    || visitor.finish_disable(data, component, context),
                )?
            }
            Control::Empty { data } => visitor
                .start_empty(data, component, context)?
                .and_then(|| visitor.finish_empty(data, component, context))?,
        }
        .apply_change(self)
    }
}
