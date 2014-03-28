from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models import (
    DBSession,
    Base,
)
from supplycrate import updaters


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    config = Configurator(settings=settings)
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('nigredo', '/nigredo')
    config.add_route('darkfinder', '/darkfinder')
    config.add_route('gooddeed', '/gooddeed')
    config.add_route('grandmaster', '/grandmaster')
    config.scan()
    app = config.make_wsgi_app()

    # session = DBSession()
    # import transaction
    # with transaction.manager:
    #     from supplycrate.views import NigredoTable
    #     nt = NigredoTable()
    #     query = nt.queryset(session)
    #     from supplycrate import utils
    #     logger = utils.get_logger()
    #     logger.debug("QUERY:")
    #     logger.debug("%s", query)
    #     raise NotImplementedError()

    updaters.register(app, settings)

    return app
