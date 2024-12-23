"""Header bar for RetPlay."""

from dash.html import Div, Img
from dash_bootstrap_components import NavbarSimple
from ret.visualisation.colourlibrary import FNC_BLUE


class RetPlayHeader(NavbarSimple):
    """A class for the header bar for RetPlay."""

    def __init__(self):
        """Create a RetPlay header bar."""
        fnc_logo = Img(src="assets/images/fnc_png.png", style={"height": "75px"})
        spacer = Div(style={"width": "10px"})
        retplay_logo = Img(src="assets/images/retplaylogowhite.png", style={"height": "75px"})
        brand = "RetPlay"
        brand_style = {"fontSize": 40}
        color = FNC_BLUE

        super().__init__(
            children=[retplay_logo, spacer, fnc_logo],
            brand=brand,
            brand_style=brand_style,
            color=color,
            dark=True,
            id="Header",
        )
