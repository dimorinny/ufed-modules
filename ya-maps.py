# -*- coding: utf8 -*-

# Выкачивает:
#    Избранные места,
#    Закладки,
#    Историю поиска.

from physical import *
import SQLiteParser
from System.Convert import IsDBNull

__author__ = "Dmitry Merkuryev"


def chromiumTimestampParse(timestamp):
    return TimeStamp.FromUnixTime(timestamp / 1000000 - 11644473600)


def commonTimestampParse(timestamp):
    return TimeStamp.FromUnixTime(timestamp / 1000)


class YandexMapsLabel(object):
    def __init__(self, databaseRecord):
        self.labelName = databaseRecord['label_name'].Value
        self.lat = databaseRecord['lat'].Value
        self.lon = databaseRecord['lon'].Value
        self.timestamp = databaseRecord['date'].Value

    def toModel(self):
        locationModel = Location()

        locationModel.Position.Value = self.parsePosition()
        locationModel.TimeStamp.Value = commonTimestampParse(self.timestamp)
        locationModel.Name.Value = self.labelName
        locationModel.Type.Value = "Закладка"
        locationModel.Category.Value = "Yandex Maps (Закладки)"
        locationModel.Deleted = DeletedState.Intact

        return locationModel

    # too lazy to do
    def parseAddress(self):
        pass

    def parsePosition(self):
        coordinateModel = Coordinate()

        coordinateModel.Longitude.Value = self.lon
        coordinateModel.Latitude.Value = self.lat

        return coordinateModel


class YandexMapsRoute(object):
    def __init__(self, databaseRecord):
        self.geocodeName = databaseRecord['geocode_name'].Value
        self.geocodeSubname = databaseRecord['geocode_subname'].Value
        self.lat = databaseRecord['lat'].Value
        self.lon = databaseRecord['lon'].Value
        self.timestamp = databaseRecord['date'].Value

    def toModel(self):
        locationModel = Location()

        locationModel.Address.Value = self.parseAddress()
        locationModel.Position.Value = self.parsePosition()
        locationModel.TimeStamp.Value = commonTimestampParse(self.timestamp)
        locationModel.Name.Value = self.geocodeName
        locationModel.Type.Value = "Маршрут"
        locationModel.Deleted = DeletedState.Intact
        locationModel.Category.Value = "Yandex Maps (Маршруты)"

        return locationModel

    # so bad method
    def parseAddress(self):
        streetAddressModel = StreetAddress()

        geocodeNameArray = self.geocodeName.split(", ")
        geocodeSubnameArray = self.geocodeSubname.split(", ")

        for index, value in enumerate(geocodeNameArray):
            if index == 0:
                streetAddressModel.Street1.Value = value

        for index, value in enumerate(geocodeSubnameArray):
            if index == 0:
                streetAddressModel.City.Value = value
            elif index == 1:
                streetAddressModel.Country.Value = value

        return streetAddressModel

    def parsePosition(self):
        coordinateModel = Coordinate()

        coordinateModel.Longitude.Value = self.lon
        coordinateModel.Latitude.Value = self.lat

        return coordinateModel


class YandexMapsParser(object):
    def __init__(self, root, extractDeleted, extractSource):
        self.root = root
        self.extractDeleted = extractDeleted
        self.extractSource = extractSource
        self.models = []
        self.source = 'Yandex Maps'

    def parse(self):
        self.mainDir = self.root.GetByPath('/databases')
        if self.mainDir is None:
            return []

        self.parseSearchHistory()
        self.parseLabels()
        self.parseRoutes()

        return self.models

    def parseLabels(self):
        dbNode = self.mainDir.GetByPath('labels.db')

        if dbNode is None or dbNode.Data is None:
            return

        db = SQLiteParser.Database.FromNode(dbNode)
        if db is None:
            return

        if 'mylabels' not in db.Tables:
            return

        ts = SQLiteParser.TableSignature('mylabels')

        if self.extractDeleted:
            SQLiteParser.Tools.AddSignatureToTable(ts, 'label_name', SQLiteParser.Tools.SignatureType.Text)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'lat', SQLiteParser.Tools.SignatureType.Long)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'lon', SQLiteParser.Tools.SignatureType.Long)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'date', SQLiteParser.Tools.SignatureType.Int48)

        for rec in db.ReadTableRecords(ts, self.extractDeleted):
            self.models.append(YandexMapsLabel(rec).toModel())

    def parseRoutes(self):
        dbNode = self.mainDir.GetByPath('routehistory.db')

        if dbNode is None or dbNode.Data is None:
            return

        db = SQLiteParser.Database.FromNode(dbNode)
        if db is None:
            return

        if 'routehistory' not in db.Tables:
            return

        ts = SQLiteParser.TableSignature('routehistory')

        if self.extractDeleted:
            SQLiteParser.Tools.AddSignatureToTable(ts, 'geocode_name', SQLiteParser.Tools.SignatureType.Text)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'geocode_subname', SQLiteParser.Tools.SignatureType.Text)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'lat', SQLiteParser.Tools.SignatureType.Long)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'lon', SQLiteParser.Tools.SignatureType.Long)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'date', SQLiteParser.Tools.SignatureType.Int48)

        for rec in db.ReadTableRecords(ts, self.extractDeleted):
            self.models.append(YandexMapsRoute(rec).toModel())

    def parseSearchHistory(self):
       	dbNode = self.mainDir.GetByPath('yandexsuggest_history.db')

        if dbNode is None or dbNode.Data is None:
            return

        db = SQLiteParser.Database.FromNode(dbNode)
        if db is None:
            return

        if 'suggest_content' not in db.Tables:
            return

        ts = SQLiteParser.TableSignature('suggest_content')

        if self.extractDeleted:
            SQLiteParser.Tools.AddSignatureToTable(ts, 'c0suggest_text_1',
                SQLiteParser.Tools.SignatureType.Null, SQLiteParser.Tools.SignatureType.Text)
            SQLiteParser.Tools.AddSignatureToTable(ts, 'c3time',
                SQLiteParser.Tools.SignatureType.Null, SQLiteParser.Tools.SignatureType.Int48)

        for rec in db.ReadTableRecords(ts, self.extractDeleted):
            vp = SearchedItem()
            vp.Source.Value = self.source

            # crunch
            vp.Deleted = DeletedState.Intact
            SQLiteParser.Tools.ReadColumnToField(rec, 'c0suggest_text_1', vp.Value, self.extractSource)
            SQLiteParser.Tools.ReadColumnToField[TimeStamp](rec, 'c3time',
                vp.TimeStamp, self.extractSource, commonTimestampParse)

            if rec['c0suggest_text_1'].Value:
                self.models.append(vp)

# getting the node from the filesystem
node = ds.FileSystems[0]['/data/data/ru.yandex.yandexmaps']

# calling the parser for results
results = YandexMapsParser(node, True, True).parse()

# adding the results to the tree view
ds.Models.AddRange(results)
