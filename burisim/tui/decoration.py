import urwid

HORIZ_BAR = '\N{BOX DRAWINGS LIGHT HORIZONTAL}'

class LabelledSeparator(urwid.WidgetWrap):
    def __init__(self, text='', bar_char=HORIZ_BAR):
        self._label = urwid.Text(text)
        cols = urwid.Columns([
            ('weight', 1, urwid.Divider(div_char=bar_char)),
            ('pack', self._label),
            ('weight', 1, urwid.Divider(div_char=bar_char)),
        ], dividechars=1)
        urwid.WidgetWrap.__init__(self, cols)

    def set_text(self, text):
        self._label.set_text(text)

    def get_text(self):
        return self._label.get_text()

    text = property(get_text)

class Window(urwid.WidgetWrap):
    #_sizing = frozenset(['box'])

    default_border = 'window border'

    # box drawing chars
    C_TL = u'\N{BOX DRAWINGS LIGHT DOWN AND RIGHT}'
    C_TL_FOCUS = u'\N{BOX DRAWINGS DOUBLE DOWN AND RIGHT}'
    C_TR = u'\N{BOX DRAWINGS LIGHT DOWN AND LEFT}'
    C_TR_FOCUS = u'\N{BOX DRAWINGS DOUBLE DOWN AND LEFT}'
    C_BL = u'\N{BOX DRAWINGS LIGHT UP AND RIGHT}'
    C_BL_FOCUS = u'\N{BOX DRAWINGS DOUBLE UP AND RIGHT}'
    C_BR = u'\N{BOX DRAWINGS LIGHT UP AND LEFT}'
    C_BR_FOCUS = u'\N{BOX DRAWINGS DOUBLE UP AND LEFT}'
    C_VERT = u'\N{BOX DRAWINGS LIGHT VERTICAL}'
    C_VERT_FOCUS = u'\N{BOX DRAWINGS DOUBLE VERTICAL}'
    C_HORIZ = u'\N{BOX DRAWINGS LIGHT HORIZONTAL}'
    C_HORIZ_FOCUS = u'\N{BOX DRAWINGS DOUBLE HORIZONTAL}'

    def __init__(self, original_widget, title=None, border_attr=None):
        self.original_widget = original_widget
        overlay = urwid.Overlay(
            original_widget, urwid.SolidFill(' '),
            'left', ('relative', 100),
            'top', ('relative', 100),
            left=1, top=1, bottom=1, right=1
        )
        urwid.WidgetWrap.__init__(self, overlay)

        self._title = title
        self._border_attr = border_attr if border_attr is not None else Window.default_border

    def set_border_attr(self, a):
        self._border_attr = a
        self._invalidate()

    def get_border_attr(self):
        return self._border_attr

    border_attr = property(get_border_attr, set_border_attr)

    def get_title(self):
        return self._title

    def set_title(self, title):
        self._title = title
        self._invalidate()

    title = property(get_title, set_title)

    def render(self, size, focus=False):
        # get canvas from underlying container
        c = urwid.CompositeCanvas(self._w.render(size))

        cw, ch = c.cols(), c.rows()

        tl = Window.C_TL_FOCUS if focus else Window.C_TL
        bl = Window.C_BL_FOCUS if focus else Window.C_BL
        tr = Window.C_TR_FOCUS if focus else Window.C_TR
        br = Window.C_BR_FOCUS if focus else Window.C_BR
        horiz = Window.C_HORIZ_FOCUS if focus else Window.C_HORIZ
        vert = Window.C_VERT_FOCUS if focus else Window.C_VERT

        # top
        w = urwid.Columns([
            (1, urwid.Text(tl)),
            #(1, urwid.Divider(horiz)),
            #('pack', urwid.Text('[\N{BLACK SMALL SQUARE}]')),
            ('weight', 1, urwid.Divider(horiz)),
            ('pack', urwid.Text([' ', self._title, ' '])),
            ('weight', 1, urwid.Divider(horiz)),
            (1, urwid.Text(tr)),
        ])
        cc = urwid.CompositeCanvas(w.render((cw,)))
        cc.fill_attr(self._border_attr)
        c.overlay(cc, 0, 0)

        # bottom
        w = urwid.Columns([
            (1, urwid.Text(bl)),
            ('weight', 1, urwid.Divider(horiz)),
            (1, urwid.Text(br)),
        ])
        cc = urwid.CompositeCanvas(w.render((cw,)))
        cc.fill_attr(self._border_attr)
        c.overlay(cc, 0, ch-1)

        if ch > 2:
            # left, right
            w = urwid.Pile([
                ('weight', 1, urwid.SolidFill(vert)),
            ])
            cc = urwid.CompositeCanvas(w.render((1, ch-2)))
            cc.fill_attr(self._border_attr)
            c.overlay(cc, 0, 1)
            c.overlay(cc, cw-1, 1)

        return c
