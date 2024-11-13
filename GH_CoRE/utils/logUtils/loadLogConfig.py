#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.6
__author__ = 'Lou Zehua'
__time__ = '2018/9/21 21:05'

import os
import json
import logging.config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def setup_logging(
        base_dir=BASE_DIR,
        default_path=None,
        default_level=logging.INFO,
        env_key='LOG_CFG'
        ):
    """
    Setup logging configuration
    You can load your own logging configuration like:
        LOG_CFG=my_new_logging.json python my_server.py
    """
    path = default_path or os.path.join(base_dir, 'etc/logging.json')
    value = os.getenv(env_key, None)
    if value:  # check if LOG_CFG valid
        path = value
    log_dir = os.path.join(base_dir, 'logs')  # default logs dir
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        f.close()
        handlers = list(config["handlers"].values())
        for handler in handlers:
            if "filename" in handler.keys():
                filename = handler["filename"]
                handler["filename"] = os.path.join(log_dir, filename)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def main():
    import logging

    from etc import pkg_rootdir

    setup_logging(base_dir=pkg_rootdir)
    logger = logging.getLogger(__name__)
    logger.info('Hi,foo')
    try:
        open('/path/does/not/exist', 'rb')
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:
        logger.error('Failed to open file', exc_info=True)


if __name__ == '__main__':
    main()
