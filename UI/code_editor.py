"""
Licensed under the terms of the MIT License
https://github.com/luchko/QCodeEditor
@author: Ivan Luchko (luchko.ivan@gmail.com)

This module contains the light QPlainTextEdit based QCodeEditor widget which
provides the line numbers bar and the syntax and the current line highlighting.

    class XMLHighlighter(QSyntaxHighlighter):
    class QCodeEditor(QPlainTextEdit):
"""

from PySide6.QtCore import QRect, QRegularExpression, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

# classes definition


class XMLHighlighter(QSyntaxHighlighter):
    """
    Class for highlighting xml text inherited from QSyntaxHighlighter

    reference:
        http://www.yasinuludag.com/blog/?p=49

    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.highlighting_rules = []

        xml_element_format = QTextCharFormat()
        xml_element_format.setForeground(QColor("#0080ff"))  # blue
        xml_element_format.setFontWeight(QFont.Bold)

        keyword_patterns = [
            "<\\?xml\\s",
            "<\\?xml-stylesheet\\s",
            "<[A-Za-z0-9_-]+(?=[\\s/>])",
            "<[A-Za-z0-9_-]+/?>",
            "</[A-Za-z0-9_-]+>",
            "\\?>",
            "/?>",
        ]
        self.highlighting_rules += [
            (QRegularExpression(pattern), xml_element_format)
            for pattern in keyword_patterns
        ]

        xml_attribute_format = QTextCharFormat()
        xml_attribute_format.setFontItalic(True)
        xml_attribute_format.setForeground(QColor("#e35e00"))  # orange
        self.highlighting_rules.append(
            (QRegularExpression("\\b[A-Za-z0-9_:]+(?=\\=)"), xml_attribute_format)
        )
        self.highlighting_rules.append((QRegularExpression("="), xml_attribute_format))

        value_format = QTextCharFormat()
        value_format.setForeground(QColor("#ffff00"))  # yellow
        self.highlighting_rules.append((QRegularExpression('"[^"]*"'), value_format))
        # self.valueStartExpression = QRegularExpression('"')
        # self.valueEndExpression = QRegularExpression('"(?=[\\s></])')

        # singleLineCommentFormat = QTextCharFormat()
        # singleLineCommentFormat.setForeground(QColor("#a0a0a4"))  # grey
        # self.highlightingRules.append(
        #     (QRegularExpression("<!--[^\n]*-->"), singleLineCommentFormat)
        # )

        # textFormat = QTextCharFormat()
        # textFormat.setForeground(QColor("#ffffff"))  # white
        # (?<=...)  - lookbehind is not supported
        # self.highlightingRules.append((QRegularExpression(">(.+)(?=</)"), textFormat))

    # VIRTUAL FUNCTION WE OVERRIDE THAT DOES ALL THE COLLORING
    def highlightBlock(self, text):
        for pattern, text_format in self.highlighting_rules:
            index = pattern.globalMatch(text)
            while index.hasNext():
                match = index.next()
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), text_format
                )

        # HANDLE QUOTATION MARKS NOW.. WE WANT TO START WITH " AND END WITH ".. A THIRD " SHOULD NOT CAUSE THE WORDS INBETWEEN SECOND AND THIRD TO BE COLORED
        # self.setCurrentBlockState(0)
        # startIndex = 0
        # if self.previousBlockState() != 1:
        #     startIndex = self.valueStartExpression.indexIn(text)
        # while startIndex >= 0:
        #     endIndex = self.valueEndExpression.indexIn(text, startIndex)
        #     if endIndex == -1:
        #         self.setCurrentBlockState(1)
        #         commentLength = len(text) - startIndex
        #     else:
        #         commentLength = (
        #             endIndex - startIndex + self.valueEndExpression.matchedLength()
        #         )
        #     self.setFormat(startIndex, commentLength, self.valueFormat)
        #     startIndex = self.valueStartExpression.indexIn(
        #         text, startIndex + commentLength
        #     )


class QCodeEditor(QPlainTextEdit):
    """
    QCodeEditor inherited from QPlainTextEdit providing:

        numberBar - set by DISPLAY_LINE_NUMBERS flag equals True
        curent line highligthing - set by HIGHLIGHT_CURRENT_LINE flag equals True
        setting up QSyntaxHighlighter

    references:
        https://john.nachtimwald.com/2009/08/19/better-qplaintextedit-with-line-numbers/
        http://doc.qt.io/qt-5/qtwidgets-widgets-codeeditor-example.html

    """

    class NumberBar(QWidget):
        """class that deifnes textEditor numberBar"""

        def __init__(self, editor):
            super().__init__(editor)

            self.editor = editor
            self.editor.blockCountChanged.connect(self.update_width)
            self.editor.updateRequest.connect(self.update_contents)
            self.font = editor.font()
            self.background_color = editor.palette().shadow().color()
            self.highlight_color = editor.palette().highlight().color()
            self.text_color = editor.palette().windowText().color()

        def paintEvent(self, event):

            painter = QPainter(self)
            painter.fillRect(event.rect(), self.background_color)

            block = self.editor.firstVisibleBlock()

            # Iterate over all visible text blocks in the document.
            while block.isValid():
                block_number = block.blockNumber()
                block_top = (
                    self.editor.blockBoundingGeometry(block)
                    .translated(self.editor.contentOffset())
                    .top()
                )

                # Check if the position of the block is out side of the visible area.
                if not block.isVisible() or block_top >= event.rect().bottom():
                    break

                # We want the line number for the selected line to be bold.
                if block_number == self.editor.textCursor().blockNumber():
                    self.font.setBold(True)
                    painter.setPen(self.highlight_color)
                else:
                    self.font.setBold(False)
                    painter.setPen(self.text_color)
                painter.setFont(self.font)

                # Draw the line number right justified at the position of the line.
                paint_rect = QRect(
                    0, block_top, self.width(), self.editor.fontMetrics().height()
                )
                painter.drawText(paint_rect, Qt.AlignRight, str(block_number + 1))

                block = block.next()

            painter.end()

            QWidget.paintEvent(self, event)

        def get_width(self):
            count = self.editor.blockCount()
            width = self.fontMetrics().size(0, str(count)).width() + 10
            return width

        def update_width(self):
            width = self.get_width()
            if self.width() != width:
                self.setFixedWidth(width)
                self.editor.setViewportMargins(width, 0, 0, 0)

        def update_contents(self, rect, scroll):
            if scroll:
                self.scroll(0, scroll)
            else:
                self.update(0, rect.y(), self.width(), rect.height())

            if rect.contains(self.editor.viewport().rect()):
                font_size = self.editor.currentCharFormat().font().pointSize()
                self.font.setPointSize(font_size)
                self.font.setStyle(QFont.StyleNormal)
                self.update_width()

    def __init__(
        self,
        display_line_numbers=True,
        highlight_current_line=True,
        syntax_highlighter=None,
    ):
        """
        Parameters
        ----------
        DISPLAY_LINE_NUMBERS : bool
            switch on/off the presence of the lines number bar
        HIGHLIGHT_CURRENT_LINE : bool
            switch on/off the current line highliting
        SyntaxHighlighter : QSyntaxHighlighter
            should be inherited from QSyntaxHighlighter
        """
        super().__init__()

        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.display_line_number = display_line_numbers

        if display_line_numbers:
            self.number_bar = self.NumberBar(self)

        if highlight_current_line:
            self.current_line_number = None
            self.current_line_color = self.palette().alternateBase()
            # self.currentLineColor = QColor("#e8e8e8")
            self.cursorPositionChanged.connect(self.highlight_current_line)

        if syntax_highlighter is not None:  # add highlighter to textdocument
            self.highlighter = syntax_highlighter(self.document())

    def resizeEvent(self, *e):
        """overload resizeEvent handler"""

        if self.display_line_number:  # resize number_bar widget
            cr = self.contentsRect()
            rec = QRect(cr.left(), cr.top(), self.number_bar.get_width(), cr.height())
            self.number_bar.setGeometry(rec)

        QPlainTextEdit.resizeEvent(self, *e)

    def highlight_current_line(self):
        new_current_line_number = self.textCursor().blockNumber()
        if new_current_line_number != self.current_line_number:
            self.current_line_number = new_current_line_number
            hi_selection = QTextEdit.ExtraSelection()
            hi_selection.format.setBackground(self.current_line_color)
            hi_selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            hi_selection.cursor = self.textCursor()
            hi_selection.cursor.clearSelection()
            self.setExtraSelections([hi_selection])
