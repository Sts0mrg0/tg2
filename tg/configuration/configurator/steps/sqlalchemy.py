# -*- coding: utf-8 -*-
from __future__ import absolute_import
from ...utils import TGConfigError
from ..base import ConfigurationStep, ConfigReadyConfigurationAction


class SQLAlchemyConfigurationStep(ConfigurationStep):
    """
    """
    id = "sqlalchemy"

    def get_actions(self):
        return (
            ConfigReadyConfigurationAction(self.setup_sqlalchemy)
        )

    def setup_sqlalchemy(self, conf, app):
        """Setup SQLAlchemy database engine"""
        engine = self.create_sqlalchemy_engine(conf)

        conf['tg.app_globals'].sa_engine = engine

        model = self._get_model(conf)
        sqla_session = model.init_model(engine)
        if sqla_session is not None:
            # If init_model returns a specific session, keep it around
            # as the SQLAlchemy Session.
            conf['SQLASession'] = sqla_session

        if 'DBSession' not in conf:
            # If the user hasn't specified a default session, assume
            # he/she uses the default DBSession in model
            conf['DBSession'] = model.DBSession

    def _get_model(self, conf):
        try:
            package_models = conf['package'].model
        except AttributeError:
            package_models = None

        model = conf.get('model', package_models)
        if model is None:
            raise TGConfigError('SQLAlchemy enabled, but no models provided')

        return model

    @staticmethod
    def create_sqlalchemy_engine(conf):
        from sqlalchemy import engine_from_config
        balanced_master = conf.get('sqlalchemy.master.url')
        if not balanced_master:
            engine = engine_from_config(conf, 'sqlalchemy.')
        else:
            engine = engine_from_config(conf, 'sqlalchemy.master.')
            conf['balanced_engines'] = {'master': engine,
                                        'slaves': {},
                                        'all': {'master': engine}}

            all_engines = conf['balanced_engines']['all']
            slaves = conf['balanced_engines']['slaves']
            for entry in conf.keys():
                if entry.startswith('sqlalchemy.slaves.'):
                    slave_path = entry.split('.')
                    slave_name = slave_path[2]
                    if slave_name == 'master':
                        raise TGConfigError('A slave node cannot be named master')
                    slave_config = '.'.join(slave_path[:3])
                    all_engines[slave_name] = slaves[slave_name] = engine_from_config(conf, slave_config + '.')

            if not conf['balanced_engines']['slaves']:
                raise TGConfigError('When running in balanced mode your must specify at least a slave node')

        return engine