import functools
import inspect
import logging
import datetime

__author__ = 'Mattia'


def get_logger():
    """
    Returns a logger whose name is the one of the calling code's module.
    """
    frm = inspect.stack()[1]
    mod = inspect.getmodule(frm[0])
    name = mod.__name__
    return logging.getLogger(name)


def decimal_str(value):
    """
    Returns a string version of a float, int or decimal value with the minimum
    number of digits after the decimal point, if any is necessary at all.
    """
    spc = str(value)
    if '.' in spc:
        while spc[-1] == '0':
            spc = spc[:-1]
        if spc[-1] == '.':
            spc = spc[:-1]
    return spc


def dump_query(statement, bind=None):
    """
    from: http://stackoverflow.com/a/5698357/909280
    dumps a query, with values filled in
    for debugging purposes *only*
    for security, you should always separate queries from their values
    please also note that this function is quite slow
    """
    import sqlalchemy.orm
    if isinstance(statement, sqlalchemy.orm.Query):
        if bind is None:
            bind = statement.session.get_bind(
                    statement._mapper_zero_or_none()
            )
        statement = statement.statement
    elif bind is None:
        bind = statement.bind

    dialect = bind.dialect
    compiler = statement._compiler(dialect)
    class LiteralCompiler(compiler.__class__):
        def visit_bindparam(
                self, bindparam, within_columns_clause=False,
                literal_binds=False, **kwargs
        ):
            return super(LiteralCompiler, self).render_literal_bindparam(
                    bindparam, within_columns_clause=within_columns_clause,
                    literal_binds=literal_binds, **kwargs
            )

    compiler = LiteralCompiler(dialect, statement)
    return compiler.process(statement)