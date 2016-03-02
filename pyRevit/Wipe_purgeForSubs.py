import clr
import StringIO
from Autodesk.Revit.DB import *

outputs = StringIO.StringIO()

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

def report(message):
	outputs.write(message)
	outputs.write('\n')
def reportAndPrint(message):
	print(message)
	outputs.write(message)
	outputs.write('\n')
def reportError( elId = 0 ):
	print('< ERROR DELETING ELEMENT ID: {0}>'.format( elId ))

report('PRINTING FULL REPORT -------------------------------------------------------------------\n')

def removeAllExternalLinks():
	t = Transaction(doc, 'Remove All External Links') 
	t.Start()
	reportAndPrint('------------------------------ REMOVE ALL EXTERNAL LINKS -------------------------------\n')
	location = doc.PathName
	modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath( location )
	transData = TransmissionData.ReadTransmissionData( modelPath )
	externalReferences = transData.GetAllExternalFileReferenceIds()

	cl = FilteredElementCollector( doc )
	impInstances = list( cl.OfClass( clr.GetClrType( ImportInstance )).ToElements() )

	imported = []

	for refId in externalReferences:
		try:
			lnk = doc.GetElement( refId )
			if isinstance( lnk, RevitLinkType) or isinstance( lnk, CADLinkType ):
				doc.Delete( refId )

		except:
			report('no')
			continue
	t.Commit()

def callPurgeCommand():
	from Autodesk.Revit.UI import PostableCommand as pc
	from Autodesk.Revit.UI import RevitCommandId as rcid
	cid_PurgeUnused = rcid.LookupPostableCommandId( pc.PurgeUnused )
	__revit__.PostCommand( cid_PurgeUnused )

tg = TransactionGroup( doc, "Purge Model for GC")
tg.Start()

removeAllExternalLinks()

tg.Commit()

callPurgeCommand()

print( outputs.getvalue() )