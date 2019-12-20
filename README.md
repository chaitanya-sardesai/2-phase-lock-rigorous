-----------------------
Pallabee Mahanta
Student ID: 1001551985
-----------------------

-----------------------
Chaiatanya Sardesai
Student ID: 1001536420
-----------------------

----------------------
Programming Language : 
----------------------
	Python version 3.6.4.
	
-------------------
Package Structure :
-------------------
	This project contains src folder, input*.txt, additional files - schedule*.txt and test*.txt and output_files.
	input*.txt has all the 7 operations.
	schedule*.txt has the 2 schedule in project description.
	test*.txt are additional testing schedule we performed.
	
	src folder has 2 python files
	RPL_2.py file, which is main file of project
	constants.py file, which is header/constant definitions file of project 
	Path:: ..\src\RPL_2.py
Note: input*.txt file shall be present at the location same as of *.py file of the project. (Above Path)

---------------
Code Structure:
---------------
	It uses 2 dataframes for transaction table and lock table
	1. Main function extracts each operation from the txt file, including the transaction id and data item if applicable, then calls respective begin(..), read(..), write(..), commit(..) functions.
	2. read and write functions checks transaction state and time stamp to grant read/write lock on given data item
	3. Times stamp of requesting transaction is compared with each and every transaction's time stamp separately which are holding the lock; if one of them is older than requesting transaction then, requesting transaction is aborted.
	4. read(..) and write(..) functions internally calls wait(..) and abort(..) functions.
	5. There are three types of results which are returned from functions: SUCCESS, IGNORE, and ABORT
	6. In case one of transaction is aborted/committed then it checks for unlocking any other blocked transactions and executes its previous commands which were ignored because it was blocked.
	7. Actions taken on all operations and final result is stored in <output_file>.txt passed through command line

------------------------
Running the Application:
------------------------ 
	1. Copy input text file at appropriate location give above.
	2. Run .py file: RPL_2.py <input_file>.txt <output_file>.txt
	3. Output file with given name will be created. Prior creation of output file is not needed
	E.g. RPL_2.py input1.txt input1_result.txt
	

-----------	
References:
-----------
1. https://stackoverflow.com/questions/38133961/pandas-how-to-store-a-list-in-a-dataframe
2. https://stackoverflow.com/questions/35956712/check-if-certain-value-is-contained-in-a-dataframe-column-in-pandas/35956886
3. Sildes chapter21, and Fundamentals of database systems(sixth edition), chapter 22.