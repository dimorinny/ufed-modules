# -*- coding: utf8 -*-

# Выкачивает:
#    Cookie Файлы,
#    Историю,
#    Логины - Пароли,
#    Историю поиска.

from physical import *
import SQLiteParser
from System.Convert import IsDBNull

__author__ = "Dmitry Merkuryev"


def chromiumTimestampParse(timestamp):
    return TimeStamp.FromUnixTime(timestamp / 1000000 - 11644473600)


class YandexBrowserParser(object):
    def __init__(self, root, extractDeleted, extractSource):
        self.root = root
        self.extractDeleted = extractDeleted
        self.extractSource = extractSource
        self.models = []
        self.source = 'Yandex Browser'

    def parse(self):
        self.mainDir = self.root.GetByPath('/app_chromium/Default')
        if self.mainDir is None:
            return []

        self.parseHistory()
        self.parseCookies()
        self.parsePasswords()
        self.parseSearchHistory()

        return self.models

    def parseHistory(self):
        dbNode = self.mainDir.GetByPath('history')

        if dbNode is None or dbNode.Data is None:
            return

        db = SQLiteParser.Database.FromNode(dbNode)
        if db is None:
            return

        if 'urls' not in db.Tables:
            return

        ts = SQLiteParser.TableSignature('urls')

        if self.extractDeleted:
            SQLiteParser.Tools.AddSignatureToTable(ts, 'url', SQLiteParser.Tools.SignatureType.Null, SQLiteParser.Tools.SignatureType.Text)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'title', SQLiteParser.Tools.SignatureType.Null, SQLiteParser.Tools.SignatureType.Text)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'visit_count', SQLiteParser.Tools.SignatureType.Const0, SQLiteParser.Tools.SignatureType.Int48)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'last_visit_time', SQLiteParser.Tools.SignatureType.Null, SQLiteParser.Tools.SignatureType.Int48)

        for rec in db.ReadTableRecords(ts, self.extractDeleted):
            vp = VisitedPage()
            vp.Source.Value = self.source

            # crunch
            vp.Deleted = DeletedState.Intact

            SQLiteParser.Tools.ReadColumnToField(rec, 'title', vp.Title, self.extractSource)
            SQLiteParser.Tools.ReadColumnToField(rec, 'url', vp.Url, self.extractSource)
            SQLiteParser.Tools.ReadColumnToField(rec, 'visit_count', vp.VisitCount, self.extractSource)
            SQLiteParser.Tools.ReadColumnToField[TimeStamp](rec, 'last_visit_time', vp.LastVisited, self.extractSource, chromiumTimestampParse)

            self.models.append(vp)

    def parsePasswords(self):
        dbNode = self.mainDir.GetByPath('Login Data')

        if dbNode is None or dbNode.Data is None:
            return

        db = SQLiteParser.Database.FromNode(dbNode)
        if db is None:
            return

        if 'logins' not in db.Tables:
            return

        ts = SQLiteParser.TableSignature('logins')

        if self.extractDeleted:
            SQLiteParser.Tools.AddSignatureToTable(ts, 'action_url', SQLiteParser.Tools.SignatureType.Text)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'username_value', SQLiteParser.Tools.SignatureType.Text)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'password_value',  SQLiteParser.Tools.SignatureType.Blob)

        for rec in db.ReadTableRecords(ts, self.extractDeleted):
            ps = Password()

            # crunch
            ps.Deleted = DeletedState.Intact

            SQLiteParser.Tools.ReadColumnToField(rec, 'action_url', ps.Service, self.extractSource)
            SQLiteParser.Tools.ReadColumnToField(rec, 'username_value', ps.Account, self.extractSource)
            ps.Data.Value = System.Text.Encoding.Default.GetString(rec['password_value'].Value)

            self.models.append(ps)

    def parseCookies(self):
        dbNode = self.mainDir.GetByPath('Cookies')
        if dbNode is None or dbNode.Data is None:
            return

        db = SQLiteParser.Database.FromNode(dbNode)
        if db is None:
            return

        if 'cookies' not in db.Tables:
            return

        ts = SQLiteParser.TableSignature('cookies')

        if self.extractDeleted:
            SQLiteParser.Tools.AddSignatureToTable(ts, 'creation_utc', SQLiteParser.Tools.SignatureType.Int)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'last_access_utc', SQLiteParser.Tools.SignatureType.Int)            
            SQLiteParser.Tools.AddSignatureToTable(ts, 'host_key', SQLiteParser.Tools.SignatureType.Text)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'name', SQLiteParser.Tools.SignatureType.Text)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'path', SQLiteParser.Tools.SignatureType.Text)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'value', SQLiteParser.Tools.SignatureType.Text)

        for rec in db.ReadTableRecords(ts, self.extractDeleted):
            c = Cookie()
            c.Deleted = rec.Deleted

            # crunch
            c.Deleted = DeletedState.Intact

            SQLiteParser.Tools.ReadColumnToField(rec, 'name', c.Name, self.extractSource)
            SQLiteParser.Tools.ReadColumnToField(rec, 'value', c.Value, self.extractSource)
            SQLiteParser.Tools.ReadColumnToField(rec, 'host_key', c.Domain, self.extractSource)
            SQLiteParser.Tools.ReadColumnToField(rec, 'path', c.Path, self.extractSource)
            SQLiteParser.Tools.ReadColumnToField[TimeStamp](rec, 'creation_utc', c.CreationTime, self.extractSource, lambda ts: TimeStamp.FromUnixTime(ts / 1000000))
            SQLiteParser.Tools.ReadColumnToField[TimeStamp](rec, 'last_access_utc', c.LastAccessTime, self.extractSource, lambda ts: TimeStamp.FromUnixTime(ts / 1000000))            

            self.models.append(c)

    def parseSearchHistory(self):
        dbNode = self.mainDir.GetByPath('history')

        if dbNode is None or dbNode.Data is None:
            return

        db = SQLiteParser.Database.FromNode(dbNode)
        if db is None:
            return

        if 'urls' not in db.Tables:
            return

        ts = SQLiteParser.TableSignature('keyword_search_terms')

        if self.extractDeleted:
            SQLiteParser.Tools.AddSignatureToTable(ts, 'term', SQLiteParser.Tools.SignatureType.Null, SQLiteParser.Tools.SignatureType.Text)

        for rec in db.ReadTableRecords(ts, self.extractDeleted):
            vp = SearchedItem()

            # crunch
            vp.Deleted = DeletedState.Intact
            vp.Source.Value = self.source

            SQLiteParser.Tools.ReadColumnToField(rec, 'term', vp.Value, self.extractSource)
            self.models.append(vp)


# getting the node from the filesystem
node = ds.FileSystems[0]['/data/data/com.yandex.browser']

# calling the parser for results
results = YandexBrowserParser(node, True, True).parse()

# adding the results to the tree view
ds.Models.AddRange(results)
