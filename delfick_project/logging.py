"""
.. autofunction:: setup_logging

.. autoclass:: LogContext
    :members:
    :member-order: bysource
"""
from datetime import datetime
from functools import partial
import logging.handlers
import traceback
import logging
import inspect
import json
import sys
import os

try:
    from rainbow_logging_handler import RainbowLoggingHandler
except ImportError:
    RainbowLoggingHandler = logging.StreamHandler


def obj_to_string(v):
    if inspect.istraceback(v):
        return " |:| ".join(traceback.format_tb(v))
    if isinstance(v, dict):
        return json.dumps(v, default=obj_to_string, sort_keys=True)
    elif hasattr(v, "as_dict"):
        return json.dumps(v.as_dict(), default=obj_to_string, sort_keys=True)
    elif isinstance(v, str):
        return v
    else:
        return repr(v)


def make_message(instance, record, oldGetMessage, program="", provide_timestamp=False):
    if isinstance(record.msg, dict):
        base = dict(record.msg)
    else:
        base = {"msg": oldGetMessage()}

    if program:
        base["program"] = program

    dc = record.__dict__
    for attr in ("name", "levelname"):
        if dc.get(attr):
            base[attr] = dc[attr]

    if provide_timestamp:
        base["@timestamp"] = datetime.utcnow().isoformat()

    if dc.get("exc_info"):
        base["traceback"] = instance.formatter.formatException(dc["exc_info"])

    if dc.get("stack_info"):
        base["stack"] = instance.formatter.formatStack(dc["stack_info"])

    return obj_to_string(base)


class SimpleFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        if "ignore_extra" in kwargs:
            ignore_extra = kwargs.pop("ignore_extra")
        else:
            ignore_extra = False

        if sys.version.startswith("2.6"):
            logging.Formatter.__init__(self, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)
        self.ignore_extra = ignore_extra

    def format(self, record):
        if self.ignore_extra:
            record.message = record.getMessage()
            return self.formatMessage(record)
        else:
            if sys.version.startswith("2.6"):
                return logging.Formatter.format(self, record)
            else:
                return super().format(record)


class SyslogHandler(logging.handlers.SysLogHandler):
    def format(self, record):
        record.getMessage = partial(make_message, self, record, record.getMessage)
        return super().format(record)


class JsonOverUDPHandler(logging.handlers.DatagramHandler):
    def __init__(self, program, host, port):
        self.program = program
        super().__init__(host, port)

    def makePickle(self, record):
        record.getMessage = partial(
            make_message,
            self,
            record,
            record.getMessage,
            program=self.program,
            provide_timestamp=True,
        )
        return "{0}\n".format(super().format(record)).encode()


class JsonOverTCPHandler(logging.handlers.SocketHandler):
    def __init__(self, program, host, port):
        self.program = program
        super().__init__(host, port)

    def makePickle(self, record):
        record.getMessage = partial(
            make_message,
            self,
            record,
            record.getMessage,
            program=self.program,
            provide_timestamp=True,
        )
        return "{0}\n".format(super().format(record)).encode()


class JsonToConsoleHandler(logging.StreamHandler):
    def __init__(self, program, stream=None):
        self.program = program
        super().__init__(stream=stream)

    def format(self, record):
        return make_message(
            self, record, record.getMessage, program=self.program, provide_timestamp=True
        )


class ConsoleHandler(RainbowLoggingHandler):
    def format(s, record):
        oldGetMessage = record.getMessage

        def newGetMessage():
            def f(v):
                def reperer(o):
                    return repr(o)

                if type(v) is dict:
                    return json.dumps(v, default=reperer, sort_keys=True)
                elif hasattr(v, "as_dict"):
                    return json.dumps(v.as_dict(), default=reperer, sort_keys=True)
                else:
                    return v

            if type(record.msg) is dict:
                s = []
                if record.msg.get("msg"):
                    s.append(record.msg["msg"])
                for k, v in sorted(record.msg.items()):
                    if k != "msg":
                        s.append("{}={}".format(k, f(v)))
                return "\t".join(s)
            else:
                return oldGetMessage()

        record.getMessage = newGetMessage
        return super().format(record)


class LogContext(object):
    """
    An object to represent logging context

    One of these is provided as ``delfick_project.logging.lc``

    You use it by doing something like:

    .. code-block:: python

        from delfick_project.logging import lc

        import logging

        log = logging.getLogger("myproject")

        log.info(lc("Some logs", var1="one"))

        ctx = lc.using(var2="two")
        log.info(ctx("message", anotherarg=1))

    Then as long as you've used :func:`~delfick_project.logging.setup_logging`
    the logger will understand the result of calling the logging context and
    display it nicely.

    For printing to the console it'll display the keyword argument as tab
    separated ``key=value`` pairs whereas all other outputs will get the log
    as a json object.

    .. automethod:: __call__
    """

    def __init__(self, initial=None, extra=None):
        self.initial = initial if initial is not None else {}
        self.context = dict(self.initial)
        if extra:
            for k, v in extra.items():
                self.context[k] = v

    def __call__(self, *args, **kwargs):
        """
        Return a dictionary of ``{"msg": " ".join(args), **kwargs}``
        """
        res = dict(self.context)
        if args:
            res["msg"] = " ".join(args)
        for k, v in kwargs.items():
            res[k] = v
        return res

    def using(self, **kwargs):
        """Return a new logging context with these extra context"""
        return LogContext(self.context, kwargs)

    def unsafe_add_context(self, key, value):
        """Mutate the current logging context"""
        self.context[key] = value
        return self


lc = LogContext()


def determine_handler(
    program, syslog_address, udp_address, tcp_address, json_to_console, logging_handler_file
):
    if syslog_address:
        address = syslog_address
        if not syslog_address.startswith("/") and ":" in syslog_address:
            split = address.split(":", 2)
            address = (split[0], int(split[1]))
        return SyslogHandler(address=address)

    if udp_address:
        return JsonOverUDPHandler(
            program, udp_address.split(":")[0], int(udp_address.split(":")[1])
        )

    if tcp_address:
        return JsonOverTCPHandler(
            program, tcp_address.split(":")[0], int(tcp_address.split(":")[1])
        )

    if json_to_console:
        return JsonToConsoleHandler(program, logging_handler_file)

    return ConsoleHandler(logging_handler_file)


def setup_logging(
    log=None,
    level=logging.INFO,
    program="",
    syslog_address="",
    tcp_address="",
    udp_address="",
    only_message=False,
    json_to_console=False,
    logging_handler_file=sys.stderr,
):
    """
    Setup the logging handlers

    .. note:: if you configure the logs to go to the console (and not as json
        strings), then they will use colors if you have
        'rainbow_logging_handler==2.2.2' installed in your python environment.

    log
        The log to add the handler to.

        * If this is a string we do logging.getLogger(log)
        * If this is None, we do logging.getLogger("")
        * Otherwise we use as is

    level
        The level we set the logging to

    program
        The program to give to the logs.

        If syslog is specified, then we give syslog this as the program.

        If tcp_address, udp_address or json_to_console is specified, then we
        create a field in the json called program with this value.

    syslog_address, tcp_address, udp_address
        If none of these is specified, then we log to the console.

        Otherwise we use the address to converse with a remote server.

        Only one will be used.

        If syslog is specified that is used, otherwise if udp is specified that is used,
        otherwise tcp.

    json_to_console
        Defaults to False. When True and we haven't specified syslog/tcp/udp address
        then write json lines to the console.

    only_message
        Whether to only print out the message when going to the console

    logging_handler_file
        The file to print to when going to the console
    """
    log = log if log is not None else logging.getLogger(log)

    handler = determine_handler(
        program, syslog_address, udp_address, tcp_address, json_to_console, logging_handler_file
    )

    # Protect against this being called multiple times
    handler.delfick_logging = True
    for h in log.handlers:
        if getattr(h, "delfick_logging", False):
            return h

    if syslog_address:
        handler.setFormatter(
            SimpleFormatter("{0}[{1}]: %(message)s".format(program, os.getpid()), ignore_extra=True)
        )
    elif udp_address or tcp_address or json_to_console:
        handler.setFormatter(SimpleFormatter("%(message)s"))
    else:
        base_format = "%(name)-15s %(message)s"
        if only_message:
            base_format = "%(message)s"

        if hasattr(handler, "_column_color"):
            handler._column_color["%(asctime)s"] = ("cyan", None, False)
            handler._column_color["%(levelname)-7s"] = ("green", None, False)
            handler._column_color["%(message)s"][logging.INFO] = ("blue", None, False)

        if only_message:
            handler.setFormatter(SimpleFormatter(base_format))
        else:
            handler.setFormatter(
                SimpleFormatter("{0} {1}".format("%(asctime)s %(levelname)-7s", base_format))
            )

    log.addHandler(handler)
    log.setLevel(level)
    return handler


def setup_logging_theme(handler, colors="light"):
    """
    Setup a logging theme

    Currently there is only ``light`` and ``dark`` which consists of a difference
    in color for INFO level messages.
    """
    if colors not in ("light", "dark"):
        logging.getLogger("delfick_project.logging").warning(
            lc("Told to set colors to a theme we don't have", got=colors, have=["light", "dark"])
        )
        return

    if hasattr(handler, "_column_color"):
        if colors == "light":
            handler._column_color["%(message)s"][logging.INFO] = ("cyan", None, False)
        else:
            handler._column_color["%(message)s"][logging.INFO] = ("blue", None, False)
