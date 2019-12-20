'''
Created on 20-Jul-2018

@author: Chaitanya
'''
import pandas as pd
import sys
import constants


'''-------------------------------------------------------------------------'''
'''                       Abort Function                                   	'''
''' Aborts the transaction; unlock all locked items by transaction			'''
''' Sets state to 'aborted'													'''
''' @params: transactnId - Transaction id which will be aborted				'''
'''			 transactnTable - Transaction table								'''
'''			 lockTable - Lock table											'''
'''			 fileObject - output file object used to write operation result '''
'''	@return: updated transactnTable and lockTable							'''
'''-------------------------------------------------------------------------'''
def abort(transactnId, transactnTable, lockTable, fileObject):
    dropCount = 0
    rowTrIndex = transactnTable[transactnTable.Tid == transactnId].index.values.astype(int)[0]
    #check if transaction is aborted or blocked, if so then ignore operation
    if transactnTable.at[rowTrIndex, 'State'] == 'aborted' or \
        transactnTable.at[rowTrIndex, 'State'] == 'blocked':
            printData = constants.dottedLine
            printData += '\nIgnore Aborted Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
            printToFile(printData, fileObject)
            return transactnTable, lockTable
    #Comes here if transaction is active.
	#Abort the transaction and update accordingly in transaction table
	#Unlock all locked data items by this transaction    
    transactnTable.at[rowTrIndex, 'State'] = 'aborted'
    transactnTable.at[rowTrIndex, 'ItemsLocked'] = []
    transactnTable.at[rowTrIndex, 'WaitingOn'] = None
    for index, dILockingTransaction in enumerate(lockTable['LockingTransaction']):
        if transactnId in dILockingTransaction:
            trIndex = dILockingTransaction.index(transactnId)
            del dILockingTransaction[trIndex]
            if not dILockingTransaction:
                lockTable = lockTable.drop(lockTable.index[[index - dropCount]])
                dropCount+=1
    
    return transactnTable, lockTable

'''-------------------------------------------------------------------------'''
'''                       Commit Function                                   '''
''' Commits/Ends the transaction; unlock all locked items by transaction	'''
''' Sets state to 'committed'												'''
''' @params: transactnId - Transaction id which will be committed			'''
'''			 transactnTable - Transaction table								'''
'''			 lockTable - Lock table											'''
'''			 fileObject - output file object used to write operation result '''
'''	@return: Success status, updated transactnTable and lockTable			'''
'''			 if transaction is blocked, return ignore status				'''
'''-------------------------------------------------------------------------'''
def commit(transactnId, transactnTable, lockTable, fileObject):
    dropCount = 0    
    rowTrIndex = transactnTable[transactnTable.Tid == transactnId].index.values.astype(int)[0]
    #check if transaction is aborted, if so then ignore operation and return success so that operation will be removed
    if transactnTable.at[rowTrIndex, 'State'] == 'aborted':
        printData = constants.dottedLine
        printData += '\nIgnore Aborted Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
        printToFile(printData, fileObject)
        return constants.STATUS_ABORTED, transactnTable, lockTable
    #check if transaction blocked, if so ignore the operation 
    if transactnTable.at[rowTrIndex, 'State'] == 'blocked':
        printData = constants.dottedLine
        printData += '\nIgnore Blocked Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
        printToFile(printData, fileObject)
        return constants.STATUS_IGNORE, transactnTable, lockTable
	#Comes here if transaction is active.
	#Commit the transaction and update accordingly in transaction table
	#Unlock all locked data items by this transaction
    transactnTable.at[rowTrIndex, 'State'] = 'committed'
    transactnTable.at[rowTrIndex, 'ItemsLocked'] = []
    transactnTable.at[rowTrIndex, 'WaitingOn'] = None
    for index, dILockingTransaction in enumerate(lockTable['LockingTransaction']):
        if transactnId in dILockingTransaction:
            trIndex = dILockingTransaction.index(transactnId)
            del dILockingTransaction[trIndex]
            if not dILockingTransaction:
                lockTable = lockTable.drop(lockTable.index[[index - dropCount]])
                dropCount+=1
                    
    return constants.STATUS_SUCCESS, transactnTable, lockTable

'''-------------------------------------------------------------------------'''
'''                       Wait/Block Function                               '''
'''	Blocks the transaction; updates transaction table; 						'''
'''	updates lock table														'''
'''	@param: transactnId - Transaction id of new transaction					'''
'''			dataItem - data item on which transaction will be waiting		'''
'''			transactnTable - Transaction table								'''
'''			lockTable - Lock table											'''
'''	@return: Updated 'transactnTable' and 'lockTable'						'''
'''-------------------------------------------------------------------------'''
def wait(transactnId, dataItem, transactnTable, lockTable):
	#get row no. from transaction table of given transaction id.
    rowTrIndex = transactnTable[transactnTable.Tid == transactnId].index.values.astype(int)[0]
	#check if transaction is already blocked
    if transactnTable.at[rowTrIndex, 'State'] == 'blocked':
        return transactnTable, lockTable
	#Comes here if transaction wasn't blocked, hence block the transaction
	#update transaction table and lock table
    transactnTable.at[rowTrIndex, 'State'] = 'blocked'
    transactnTable.at[rowTrIndex, 'WaitingOn'] = dataItem
    
    rowLckIndex = lockTable[lockTable.Items == dataItem].index.values.astype(int)[0]
    lockTable.at[rowLckIndex, 'TransactionsWaiting'].append(transactnId)  
    return transactnTable, lockTable

'''-------------------------------------------------------------------------'''
'''                       Begin Function                                    '''
''' Adds new entry to transaction table with all details: transaction id,	'''
'''	time stamp, and sets state to active state								'''
'''	@params: transactnId - Transaction id of new transaction				'''
'''			 timeStamp - time stamp at which transaction has started		'''
'''			 transactnTable - Transaction table								'''
'''	@return: Updated transaction table(transactnTable) 						'''
'''-------------------------------------------------------------------------'''
def begin(transactnId, timeStamp, transactnTable):
    transactnTable = transactnTable.append({'Tid': transactnId, 'TimeStamp': timeStamp, 'State': 'active',\
                                            'ItemsLocked': [], 'WaitingOn': None}, ignore_index=True)
    return transactnTable

'''-------------------------------------------------------------------------'''
'''                       Read Function                                    '''
'''	Acquire read lock for given transaction with given data item			'''
'''	Calls wait(..), abort(..), printToFile(..) internally					'''
'''	According to time stamp and lock state blocks or aborts the transaction	'''
'''	@params: transactnId - Transaction id of request lock					'''
'''			 dataItem - Data item on which lock has been requested			'''
'''			 reCheckFlag - if true, check if transaction can be unblocked	'''
'''						   else, if blocked, ignore the operation			'''
'''			 transactnTable - Transaction table								'''
'''			 lockTable - Lock table											'''
'''			 fileObject - output file object used to write operation result '''
'''-------------------------------------------------------------------------''' 
def read(transactnId,dataItem,transactnTable,lockTable,reCheckFlag, fileObject):  
	#check if transaction id already exits in transacrion table  
    if any(transactnTable.Tid == transactnId):
		#get the row no. from the transaction table of the given transaction id 
        rowTrIndex = transactnTable[transactnTable.Tid == transactnId].index.values.astype(int)[0]
		#get the timestamp of the transaction
        timeStampOfRequestingTr = transactnTable.at[rowTrIndex, 'TimeStamp']
        #check if transaction is aborted, if aborted ignore the operation and return success so that it will be deleted
        if transactnTable.at[rowTrIndex, 'State'] == 'aborted':
            printData = constants.dottedLine
            printData += '\nIgnore Aborted Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
            printToFile(printData, fileObject)
            return constants.STATUS_ABORTED, transactnTable, lockTable
		#check if transaction is blocked, if so ignore the the operation
		#reCheckFlag = false represents transaction cannot be unblocked
        if transactnTable.at[rowTrIndex, 'State'] == 'blocked' and reCheckFlag!=True:
            printData = constants.dottedLine
            printData += '\nIgnore Blocked Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
            printToFile(printData, fileObject)
            return constants.STATUS_IGNORE,transactnTable,lockTable
        #check if requested data item already present in lock table
        elif any(lockTable.Items == dataItem):     
			#get the row no. from the lock table where that data item exists		
            rowLckIndex = lockTable[lockTable.Items == dataItem].index.values.astype(int)[0]
			#check if already wl lock is on that data item
            if lockTable.at[rowLckIndex, 'LockState'] == 'wl':
				#get the time stamp of transaction which is holding the wl lock
                holdingTidList = lockTable.at[rowLckIndex, 'LockingTransaction']
                rowIndex = transactnTable[transactnTable.Tid == holdingTidList[0]].index.values.astype(int)[0]              
                timeStampOfHoldingTr = transactnTable.at[rowIndex, 'TimeStamp']
				#check if requesting transaction is younger
                if timeStampOfRequestingTr > timeStampOfHoldingTr:
					#lock requesting transaction is younger; abort the transaction
                    transactnTable, lockTable = abort(transactnId, transactnTable, lockTable, fileObject)
                    printData = constants.dottedLine
                    printData += '\nAbort Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
                    printToFile(printData, fileObject)
                    return constants.STATUS_ABORT,transactnTable,lockTable
                else:
					#lock requesting transaction is older; block the transaction
                    transactnTable, lockTable = wait(transactnId, dataItem, transactnTable, lockTable)
                    printData = constants.dottedLine
                    printData += '\nBlock Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
                    printToFile(printData, fileObject)
                    return constants.STATUS_IGNORE,transactnTable,lockTable
            else:
				#No locks on data item, grant lock to requesting transaction
                lockTable.at[rowLckIndex, 'LockingTransaction'].append(transactnId)
                transactnTable.at[rowTrIndex,'ItemsLocked'].append([dataItem,'rl'])
                return constants.STATUS_SUCCESS,transactnTable,lockTable
        else:
			#data item is not present in lock table, hence no locks on data item, grant lock to requesting transaction
			#In case requesting transaction is blocked and recheckFlag is True, unblock it and grant access to data item.
            if transactnTable.at[rowTrIndex, 'State'] == 'blocked' and reCheckFlag:
                printData = constants.dottedLine
                printData += '\nActive again Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
                printToFile(printData, fileObject)
                transactnTable.at[rowTrIndex, 'State'] = 'active'
                transactnTable.at[rowTrIndex, 'WaitingOn'] = None
			#Add entries to transaction table and lock table 
            lockTable = lockTable.append({'Items':dataItem,'LockState':"rl",'LockingTransaction':[transactnId],\
                                         'TransactionsWaiting':[]},ignore_index=True)
            transactnTable.at[rowTrIndex, 'ItemsLocked'].append([dataItem, 'rl'])
            return constants.STATUS_SUCCESS,transactnTable,lockTable
    return constants.STATUS_IGNORE, transactnTable, lockTable

'''-------------------------------------------------------------------------'''
'''                       Write Function                                    '''
'''	Acquire write lock for given transaction with given data item			'''
'''	Calls wait(..), abort(..), printToFile(..) internally					'''
'''	According to time stamp and lock state blocks or aborts the transaction	'''
'''	@params: transactnId - Transaction id of request lock					'''
'''			 dataItem - Data item on which lock has been requested			'''
'''			 reCheckFlag - if true, check if transaction can be unblocked	'''
'''						   else, if blocked, ignore the operation			'''
'''			 transactnTable - Transaction table								'''
'''			 lockTable - Lock table											'''
'''			 fileObject - output file object used to write operation result '''
'''-------------------------------------------------------------------------'''    
def write(transactnId, dataItem, reCheckFlag, transactnTable, lockTable, fileObject):
	#check if transaction id already exits in transacrion table
    if any(transactnTable.Tid == transactnId):
		#get the row no. from the transaction table of the given transaction id 
        rowTrIndex = transactnTable[transactnTable.Tid == transactnId].index.values.astype(int)[0]
		#get the timestamp of the transaction
        timeStampOfRequestingTr = transactnTable.at[rowTrIndex, 'TimeStamp']
        #check if transaction is aborted, if aborted ignore the operation and return success so that it will be deleted
        if transactnTable.at[rowTrIndex, 'State'] == 'aborted':
            printData = constants.dottedLine
            printData += '\nIgnore Aborted Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
            printToFile(printData, fileObject)
            return constants.STATUS_ABORTED, transactnTable, lockTable
        #check if transaction is blocked, if so ignore the the operation
		#reCheckFlag = false represents transaction cannot be unblocked
        if transactnTable.at[rowTrIndex, 'State'] == 'blocked' and reCheckFlag!=True:
            printData = constants.dottedLine
            printData += '\nIgnore Blocked Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
            printToFile(printData, fileObject)
            return constants.STATUS_IGNORE, transactnTable, lockTable
        #check if requested data item already present in lock table
        elif any(lockTable.Items == dataItem):  
			#get the row no. from the lock table where that data item exists
            rowLckIndex = lockTable[lockTable.Items == dataItem].index.values.astype(int)[0]
			#check if already rl or wl lock is on that data item
            if lockTable.at[rowLckIndex, 'LockState'] == 'rl' or \
                lockTable.at[rowLckIndex, 'LockState'] == 'wl':
                transactnList = lockTable.at[rowLckIndex, 'LockingTransaction']
				#check if only 1 transaction has the lock
                if len(transactnList) == 1:
					#check if same transaction which has rl lock try to get wl on data item 
                    if transactnList[0] == transactnId:
                        #upgrade
                        if transactnTable.at[rowTrIndex, 'State'] == 'blocked' and reCheckFlag:
                            printData = constants.dottedLine
                            printData += '\nActive again Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
                            printToFile(printData, fileObject)
                            transactnTable.at[rowTrIndex, 'State'] = 'active'
                            transactnTable.at[rowTrIndex, 'WaitingOn'] = None
                            
                            #delete transaction id from lock table column "transaction Waiting"
                            delTrIndex = lockTable.at[rowLckIndex, 'TransactionsWaiting'].index(transactnId)
                            trWaitingList = lockTable.at[rowLckIndex, 'TransactionsWaiting']
                            del trWaitingList[delTrIndex]
                            lockTable.at[rowLckIndex, 'TransactionsWaiting'] = trWaitingList
                        
						#add one more data item with 'wl' to transaction table under items locked column
                        lockTable.at[rowLckIndex, 'LockState'] = 'wl'
                        tr = transactnTable.at[rowTrIndex, 'ItemsLocked']
                        for i in range(len(tr)):
                            if tr[i] == [dataItem,"rl"]:
                                tr[i] = [dataItem,"wl"]
                        transactnTable.at[rowTrIndex, 'ItemsLocked'] = tr                        
                        return constants.STATUS_SUCCESS, transactnTable, lockTable
				#Comes here if already rl or wl lock is present by another transaction/s
                for transaction in transactnList:
					#check time stamp of every transaction with requesting transaction's time stamp
                    rowIndex = transactnTable[transactnTable.Tid == transaction].index.values.astype(int)[0]
                    if timeStampOfRequestingTr > transactnTable.at[rowIndex, 'TimeStamp']:
						#requesting transaction is younger; abort the transaction
                        transactnTable, lockTable = abort(transactnId, transactnTable, lockTable, fileObject)
                        printData = constants.dottedLine
                        printData += '\nAbort Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
                        printToFile(printData, fileObject)
                        return constants.STATUS_ABORT, transactnTable, lockTable
				#requesting transaction is older; block the requesting transaction
                transactnTable, lockTable = wait(transactnId, dataItem, transactnTable, lockTable)
                printData = constants.dottedLine
                printData += '\nBlock Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
                printToFile(printData, fileObject)
                return constants.STATUS_IGNORE, transactnTable, lockTable
        else:
			#Comes here if data item doesn't exists in lock table, hence lock can be granted
			#In case transaction is blocked/waiting on data item and recheckFlag is True, activate transaction and grant the lock
            if transactnTable.at[rowTrIndex, 'State'] == 'blocked' and reCheckFlag:
                printData = constants.dottedLine
                printData += '\nActive again Transaction ' + str(transactnTable.at[rowTrIndex, 'Tid'])
                printToFile(printData, fileObject)
                transactnTable.at[rowTrIndex, 'State'] = 'active'
                transactnTable.at[rowTrIndex, 'WaitingOn'] = None
			#add entries to transaction table and lock table
            lockTable = lockTable.append({'Items': dataItem, 'LockState': 'wl', 'LockingTransaction': [transactnId], 
                                'TransactionsWaiting': []}, ignore_index=True)
            transactnTable.at[rowTrIndex, 'ItemsLocked'].append([dataItem,"wl"])
            return constants.STATUS_SUCCESS, transactnTable, lockTable
    return constants.STATUS_IGNORE, transactnTable, lockTable

'''-------------------------------------------------------------------------'''
'''                       open output file Function							'''
''' Opens the output file in append mode									'''
'''	@param: fileName - Name of the ouput file								'''
''' @return: opened file object												'''
'''-------------------------------------------------------------------------'''
def openOutputFile(fileName):
    try:
        fObj = open(fileName,'a+')
    except:
        sys.exit("\nError opening output file.\nCheck file name.\n")
    return fObj

'''-------------------------------------------------------------------------'''
'''                       close output file Function						'''
''' Closed the output file													'''
'''	@param: fileObject - Object of file which needs to be closed			'''
'''-------------------------------------------------------------------------'''
def closeOutputFile(fileObject):
    fileObject.close()

'''-------------------------------------------------------------------------'''
'''                       print to file Function							'''
''' Writes to the file														'''
'''	File needs to be opened before calling this function					'''
'''	@param: data - Data in string format which will be written on file		'''
'''			fileObject - Object of file on which data will be written		'''
'''-------------------------------------------------------------------------'''    
def printToFile(data, fileObject):
    fileObject.write(data)
    
'''-------------------------------------------------------------------------'''
'''                       Main Function                                     '''
''' Main routine to execute operation sequentially, by extracting 			'''
''' transaction id and data item											'''
'''	Calls begin(..), read(..), write(..), commit(..) functions internally	'''
'''	Write transaction table and lock table after execution of every			'''
''' operation to a output file, including final resulting tables			'''
'''	@params: argv - command line arguments, containing input file name and	'''
'''					ouput file name											'''
'''-------------------------------------------------------------------------'''
def main(argv):
    #Check input and output file names are provided through command line
    if len(argv) != 3:
        print('Two command-line arguments are needed:')
        print('Usage: %s [input_file_Name] [output_file_name]' % argv[0])
        sys.exit(2)
	#get input and output file names 
    inputFileName = argv[constants.OFFS_INPUT_FILE_NAME]
    outputFileName = argv[constants.OFFS_OUTPUT_FILE_NAME]    
    
	#Declare Transaction table and Lock table
    reCheckFlag = False
    timeStamp = 0
    transactnTable = pd.DataFrame(columns=['Tid', 'TimeStamp', 'State', 'ItemsLocked', \
                                           'WaitingOn'])
    transactnTable = transactnTable.astype('object')
    lockTable = pd.DataFrame(columns=['Items','LockState','LockingTransaction', \
                                      'TransactionsWaiting'])
    lockTable = lockTable.astype('object')

    # Try to open the input file
    try:
        fObj = open(inputFileName,'r+')
    except:
        sys.exit("\nError opening input file.\nCheck file name.\n")
    fileLines= list(map(str.strip, fObj.read().split(';')))
    fObj.close()
    
    # Try to open the output file
    fileObject = openOutputFile(outputFileName)
    
    LinesIndex = 0
	#Read first operation 
    line = fileLines[LinesIndex]
    #for line in lines:
    while len(line):
        printData = constants.dottedLine
        printData += constants.dottedLine + '\n' + str(line)
        printData += '\n'
		#write operation to file
        printToFile(printData, fileObject)
			
        if line[constants.OFFS_OPERATION] == constants.BEGIN_OPERATION:
			#Operation is bi (Begin i)
            transactnId = line[constants.OFFS_TRANSACTION_ID]
            timeStamp += 1
            transactnTable = begin(transactnId, timeStamp, transactnTable)
            reCheckFlag = False
            del fileLines[LinesIndex]            
            printData = "\nBegin T"+transactnId+'\n\n'+str(transactnTable) + '\n' + str(lockTable) + constants.dottedLine
            printToFile(printData, fileObject)
            
        elif line[constants.OFFS_OPERATION] == constants.READ_OPERATION:
            #Operation is ri(data_item) (read operation by i on data item)
			#retrive data item and transaction id i	
            transactnId = line[constants.OFFS_TRANSACTION_ID]
            dataItem = line[line.index('(')+1]
            success, transactnTable, lockTable = read(transactnId,dataItem,transactnTable,lockTable,\
                                                      reCheckFlag, fileObject)
            if success == constants.STATUS_ABORT:
				#Come here if because of the read operation transaction got aborted                
                del fileLines[LinesIndex]
                printData = "\nIgnore as T"+ transactnId +" was aborted"
				#reinitialize the pointer to operation in file to 0.(Try to execute previous commands that coudn't be executed)
                LinesIndex = 0
                reCheckFlag = True                
            elif success == constants.STATUS_SUCCESS:
				#Come here if read operation(read lock) by transaction was successful                
                reCheckFlag = False
                del fileLines[LinesIndex]
                printData = "\nRead lock acquired by T"+transactnId+ " on "+dataItem
            elif success == constants.STATUS_IGNORE:
				#Come here if operation was ignored because transaction was blocked(waiting)
                reCheckFlag = False
                printData = "\nIgnore T"+ transactnId
				#Increment and get next operation
                LinesIndex += 1
            elif success == constants.STATUS_ABORTED:
                #Come here if transaction was aborted
                reCheckFlag = False
                del fileLines[LinesIndex]
                printData = "\nT"+transactnId+ " was Aborted"
            #write resulting tables to file
            printData += '\n\n'
            printData += str(transactnTable) + '\n' + str(lockTable) + constants.dottedLine
            printToFile(printData, fileObject)
            
        elif line[constants.OFFS_OPERATION] == constants.WRITE_OPERATION:
			#Operation is wi(data_item) (write operation by i on data item)
			#retrive data item and transaction id i
            transactnId = line[constants.OFFS_TRANSACTION_ID]
            dataItem = line[line.index('(')+1]
            success, transactnTable, lockTable = write(transactnId, dataItem, reCheckFlag, \
                                                       transactnTable, lockTable, fileObject)
            if success == constants.STATUS_ABORT:
				#Come here if because of the write operation transaction got aborted
                del fileLines[LinesIndex]
                reCheckFlag = True
                printData = "\nIgnore as T"+ transactnId +"was aborted"
				#reinitialize the pointer to operation in file to 0.(Try to execute previous commands that coudn't be executed)
                LinesIndex = 0 
                #print(fileLines)
            elif success == constants.STATUS_SUCCESS:
				#Come here if read operation(read lock) by transaction was successful
                reCheckFlag = False
                del fileLines[LinesIndex]
                printData = "\nWrite lock acquired by T"+transactnId+ " on "+dataItem
            elif success == constants.STATUS_IGNORE:
                #Come here if operation was ignored because transaction was blocked(waiting)
                reCheckFlag = False
                printData = "\nIgnore T"+ transactnId
				#Increment and get next operation
                LinesIndex += 1
            elif success == constants.STATUS_ABORTED:
                #Come here if transaction was aborted
                reCheckFlag = False
                del fileLines[LinesIndex]
                printData = "\nT"+transactnId+ " was Aborted"
			#write resulting tables to file
            printData += '\n\n'
            printData += str(transactnTable) + '\n' + str(lockTable) + constants.dottedLine
            printToFile(printData, fileObject)
            
        elif line[constants.OFFS_OPERATION] == constants.END_OPERATION:
            #Operation is ei (end (commit) operation of transaction i)
			#retrive transaction id i
            transactnId = line[constants.OFFS_TRANSACTION_ID]
            success, transactnTable, lockTable = commit(transactnId, transactnTable, lockTable, fileObject)
            if success == constants.STATUS_SUCCESS:
				#Come here if successfully commited 
                del fileLines[LinesIndex]
                reCheckFlag = True
                printData = "\nT"+transactnId+" Committed"
				#reinitialize the pointer to operation in file to 0.(Try to execute previous commands that coudn't be executed)
                LinesIndex = 0
            elif success == constants.STATUS_IGNORE:
				#Come here if transaction is blocked(waiting) already
				#increment operation pointer
                LinesIndex += 1
                reCheckFlag = False
                printData = "\nIgnore T"+ transactnId
            elif success == constants.STATUS_ABORTED:
                #Come here if transaction was aborted
                reCheckFlag = False
                del fileLines[LinesIndex]
                printData = "\nT"+transactnId+ " was Aborted"
			#write resulting tables to file
            printData += '\n\n'
            printData += str(transactnTable) + '\n' + str(lockTable) + constants.dottedLine
            printToFile(printData, fileObject)
		#get new operation, LinesIndex is modified pointer to operations
        line = fileLines[LinesIndex]
    #Write final result to the file
    printData = constants.dottedLine+ '\n'
    printData += constants.dottedLine + '\n' + str(transactnTable) + constants.dottedLine + '\n' + str(lockTable) + constants.dottedLine + '\n'
    printToFile(printData, fileObject)
    closeOutputFile(fileObject)
    return

if __name__ == '__main__':
    main(sys.argv)