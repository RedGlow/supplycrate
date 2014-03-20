from pyramid.view import view_config
from supplycrate.controllers.nigredo import NigredoTable
from supplycrate.controllers.darkfinder import DarkfinderTable
from supplycrate.controllers.gooddeed import GoodDeedTable
from supplycrate.tablerenderer.view import table_render
from supplycrate import utils


logger = utils.get_logger()


@view_config(route_name='nigredo')
def nigredo_view(request):
    return table_render(request, NigredoTable)


@view_config(route_name='darkfinder')
def darkfinder_view(request):
    return table_render(request, DarkfinderTable)


@view_config(route_name='gooddeed')
def gooddeed_view(rquest):
    return table_render(request, GoodDeedTable)