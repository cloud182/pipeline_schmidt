#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Pipeline di riduzione base dati Schimdt per nuovo CCD.
Autore: Enrico Congiu

Istruzioni:
La pipeline può essere lanciata da qualsiasi cartella, una volta impostato
il path della cartella di lavoro con tutti i file originali.
Poi si seleziona la sezione delle immagini da trimmare.
Le immagini devono avere tutte lo stesso binning.

Ogni funzione ha un header che spiega in maggior dettaglio il suo funzionamento.

'''


import numpy as np
from pyraf import iraf
import os
import sys

iraf.noao(_doprint=0)
iraf.imred(_doprint=0)
iraf.irred(_doprint=0)


############################ CARTELLE ##############################

'''
Crea cartelle per ordinare i file in base al tipo e al filtro.
Se il file org.log viene trovato nella directory le subdirectory non vengono create.
Input:
    - Tabella = tabella con le informazioni che esce da HSEL
    - main_dir = directory di lavoro, default = ./
    - debug = opzione per avere output aggiuntivi
Output
    - Crea cartelle:
        bias
        dark
        filtri:
                flat
                objects
    - filtri = lista con nomi dei filtri utilizzati
    - bias_dir = path della directory dei bias
    - dark_dir = path directory dark

'''
def cartelle(tabella, main_dir = './', debug=False):
    
    bias_dir = main_dir+'bias/'
    dark_dir = main_dir+'dark/'
    if not os.path.exists(main_dir+'org.log'):
        os.system('mkdir '+bias_dir)                         #creo cartella bias
        os.system('mkdir '+dark_dir)                         #creo cartella dark

    filtri =[]                                               #individuo i filtri usati
    for item in tabella['filter']:
        if item not in filtri:
            filtri.append(item)
    if debug:
        print filtri
    if not os.path.exists(main_dir+'org.log'):
        for item in filtri:
            os.system('mkdir '+main_dir+item)                #creo sottocartelle per filti, oggetti e flats
            os.system('mkdir '+main_dir+item+'/objects')
            os.system('mkdir '+main_dir+item+'/flats')
    return filtri, bias_dir, dark_dir

############################# COMBINE ###############################

'''
Usa imcombine per combinare le immagini. Crea una lista temporanea per
imcombine con le immagini da combinare, aggiungendo l'estensione corretta,
poi procede con la combinazione

Input:
    - lista = lista delle immagini
    - extension = estensione da aggiungere ai file di input
    - out = nome del file di output
    - main_dir = directory di lavoro, default = './'
    - comb = metodo di combinazione, default = median
    - rej = criterio per la rejection, default = minmax
    - low = numero di pixel con il valore più basso da rifiutare, default = 1
    - high = numero di pixel con il valore più alto da rifiutare, default = 1
    - debug = per ora inutilizzato
Output
    - immagine combinata con imcombine
'''

def combine(lista, extension, out, main_dir = './', comb= 'median', rej ='minmax', low = '1', high='1', debug = False):
    f = open('tmp_inp','w')
    for item in lista:
        print >>f, main_dir+item+extension
    f.close()
    inp='@tmp_inp' 
    iraf.imcombine(inp, output = main_dir+out, combine = comb, reject = rej, nlow = low, nhigh=high)
    os.remove('tmp_inp')


############################### HSEL #################################

'''
Crea una lista con le caratteristiche delle osservazioni utilizzando hselect. 

Input:
    - files = nome del file, come su iraf
    - field = campi da estrarre con hselect, default = '$I,OBJECT,IMAGETYP,FILTER,EXPTIME,AIRMASS'
              per il settagio di seguito sno gli unici ora supportati
    - main_dir = directory di lavoro, default = './'
    - debug = stampa output aggiuntivi, default = False

Output
    - ss = tabella con le informazioni selezionate
'''
def hsel(files, field = '$I,OBJECT,IMAGETYP,FILTER,EXPTIME,AIRMASS', main_dir='./', debug=False):
    s = iraf.hselect(files,fields = field, expr='yes',Stdout=1)
    f=open(main_dir+'list_tmp','w')
    l = len(main_dir)
    for i in s:
        print >>f, i[l:]
        if debug:
            print i
    f.close()
    ss = np.genfromtxt(main_dir+'list_tmp',delimiter='\t', dtype=[('name','S7'),('obj','S15'),('type','S7') ,('filter','S2'),('texp','d'), ('airmass','f')])
    if not debug:
        os.remove(main_dir+'list_tmp')
    return ss

############################# LINEARIZE ###############################
'''
Usa irlincor per linearizzare le immagini del CCD Schmidt
Input:
    - inp = nome immagine come da IRAF
    - out = nome immagine di output, come da IRAF
    - coeff1, ..., coeff3 = coefficienti per la linearizzazione. Default valori per CCD nuovo
    CCD nuovo = [1., -0.10140076, 0.034650755]
    SBIG = [1., 0., 0.0133]
'''
#linearizzazione immagini
def linearize(inp, out, co1 = 1., co2 = -0.10140076, co3 = 0.034650755, debug = False):
    iraf.irlincor(input = inp, output = out, coeff1 = co1, coeff2 = co2, coeff3 = co3)

############################# OPERATION ###############################

'''

Usa imarith per fare operazioni tra immagini.
Input:
    - val1 = immagine 1
    - val2 = immagine 2
    - operator = tipo di operatore (+,-,/,*)
    - out = immagine di output
    - debug = inutilizzato per ora

'''

def operation(val1, val2, operator, out, debug = False):
    iraf.imarith(val1, operator, val2, out)

############################# ORGANIZZA ###############################

'''
Organizza i file. La prima volta che viene lanciato crea un file di log.
Se durante un esecuzione il file di log viene trovato nella cartella 
i file non vengono spostati. (forse devo trovare un modo migliore)

Input:
    - tabella = tabella con i file proveniente da HSEL
    - main_dir = directory di lavoro, default = './'
    - debug = stampa output aggiuntivi, default = False
Output:
    - filtri = lista con nomi dei filtri utilizzati
    - bias_dir = path della directory dei bias
    - dark_dir = path directory dark
'''
def organizza(tabella, main_dir = './', debug = False):
    l = len(tabella['name'])
    filtri, bias_dir, dark_dir = cartelle(tabella, main_dir=main_dir)
    if not os.path.exists(main_dir+'org.log'):
        for i in range(l):
            if tabella['type'][i] == 'Bias':
                os.system('cp '+main_dir+tabella['name'][i]+'.fits'+' '+main_dir+'bias')
                if debug: print tabella['name'][i]+'.fits'+' in '+main_dir+'bias'
            elif tabella['type'][i] == 'Dark':
                os.system('cp '+main_dir+tabella['name'][i]+'.fits'+' '+main_dir+'dark')
                if debug: print tabella['name'][i]+'.fits'+' in '+main_dir+'dark'
            elif tabella['type'][i] == 'Flat':
                for item in filtri:
                    if tabella['filter'][i] == item:
                        os.system('cp '+main_dir+tabella['name'][i]+'.fits'+' '+main_dir+item+'/flats')
                        if debug: print tabella['name'][i]+'.fits'+' in '+main_dir+item+'/flats'
            elif tabella['type'][i] == 'Object':
                for item in filtri:
                    if tabella['filter'][i] == item:
                        os.system('cp '+main_dir+tabella['name'][i]+'.fits'+' '+main_dir+item+'/objects')
                        if debug: print tabella['name'][i]+'.fits'+' in '+main_dir+item+'/objects'   
        f = open(main_dir+'org.log','w')
        print >>f, 'The software has already been lunched on this dataset'
        f.close()
    else:
        print 'La ppeline è gia stata usata in questa cartella.'
        print 'Cancella le vecchie cartelle se la vuoi usare'
        print 'di nuovo.'
        print '#############################################'
        sys.exit()

    return filtri, bias_dir, dark_dir

############################# PRINT_LIST ###############################
'''

Stampa una lista su file.
Input:
    - lista = lista da stampare
    - nomefile = nome del file da creare
    - debug = inutilizzato
'''

#stampa una lista su file.
def print_list(lista, nomefile, main_dir = './', debug = False):
    f=open(main_dir+nomefile,'w')
    for i in lista:
        if debug:
            print main_dir+i
        print >>f, main_dir+i
    f.close()

############################## SEPARA ###################################
'''
Crea lista di file a partire dalla lista delle osservazioni.  
Input:
    - lista = lista delle osservazioni
    - field = colonna del file su cui cercare se la condizione è verificata
    - value = valore da cercare nella colonna
    - debug = stampa valori aggiuntivi, default = False
Output:
    - output = lista richiesta
'''
## crea liste di files a partire dalla lista delle osservazioni.
def separa(lista, field, value, debug=False):
    output = []
    for i in range(len(lista[field])):
        if debug:
            print lista[field][i]
        if lista[field][i] == value:
            output.append(lista['name'][i])
    return output

############################## STATS #####################################
'''
Usa imstat per fare statistica sulle immagini.
Input:
    - lista = lista di immagini da analizzare
    - extension = estensione del file da analizzare
    - main_dir = directory di lavoro, default = './'
    - field = valore statistico ricercato
    - debug = non utilizzato
output:
    - out2 = statistica richiesta
'''
def stats(lista, extension, main_dir = './', field = 'midpt', debug = False):
    out= []
    out2 = []
    for item in lista:
        out.append(iraf.imstat(main_dir+item+extension, fields = field, Stdout=1))
    for i in range(len(out)):
        out2.append(out[i][1])
    out2=np.array(out2, dtype='d')
    return out2

############################## TRIM #######################################

'''
Usa imcopy per tagliare le immagini.
Input:
    - lista = lista delle immagini da trimmare
    - main_dir = directory di lavoro, default = './'
    - section = sezione dell'immagine per il trimming
    - debug = non utilizzato
'''
def trim(lista, main_dir = './', section ='[100:3996,100:3996]', debug=False):
    for i in lista: 
        obj = main_dir+'%s%s' % (i, section)
        out = main_dir+'%s.tr.fits' % i
        iraf.imcopy(obj,output=out)

############################ PIPELINE #####################################


'''
Codice principale della pipeline. E' scritto come una funzione, in modo che 
sia possibile usarlo in modo un po' più elastico e ordinato.

Funzionamento:
1. Il programma crea una lista temporanea dei file fits nella cartella,
   estrae le informazioni importanti:
    -nome file
    -target
    -tipo di immagine
    -filtro
    -tempo di esposizione
    -airmass

2. Crea delle cartelle per bias e dark e copia quei file all'interno delle suddette cartelle.
3. Controla anche tutti i filtri utilizzati durante la notte e divide flats e immagini scientifiche 
   in cartelle in base ai filtri utilizzati.
4. Taglia i bias e crea il masterbias
5. Taglia i dark, li corregge per bias, li linearizza e combina creando il master_bias
6. per ogni filtro taglia i flat, li corregge per bias, li linearizza, normalizza e combina creando il masterflat
7. Idem come sopra per i target, ma corregge anche per dark e per flat.

Input:
    - main_dir = directory di lavoro non c'è default qui.
    - trim_section = sezione di trimming
    - co1, ... , co3 = coefficienti per linearize per la linearizzazione delle immagini
      default = CCD nuovo schmidt 
      CCD nuovo = [1., -0.10140076, 0.034650755]
      SBIG = [1., 0., 0.0133]
Output:
    Gli output sono tutti files:
        - mbias.fits = masterbias
        - dark*.fits = master dark per i diversi tempi di esposizione
        - mflat*.fits = master flats per ogni filtro
        - *.b.fits = file corretti per bias
        - *.l.fits = file linearizzati
        - *.d.fits = file corretti per dark
        - *.f.fits = file corretti per flat
        - *.n.fits = flat normalizzati
        
'''

#pipeline
def pipeline(main_dir, trim_section, co1 = 1, co2 = -0.10140076, co3 = 0.034650755, debug = False):                                                      
    obs_list = hsel(main_dir+'*.fits', main_dir=main_dir, debug = debug)             #creo tabella con i file e i dati delle immagini


    print '############ Organizing ##############'                          

    '''
    Organizzo i file e mi tiro fuori la lista dei filtri
    e le cartelle di dark e bias. Chiedo un input in modo che 
    l'utente possa controllare se tutto ok.

    '''
    filtri, bias_dir, dark_dir = organizza(obs_list, \
            main_dir= main_dir, debug = debug)                             

    question = raw_input('Continue? y/n ')
    if question not in ['y','Y','yes','Yes']:
        sys.exit()


    print '############ Master Bias #############'
    '''
    Creazione del masterbias. 
    
    Prima seleziono i bias dalla lista
    delle osservazioni, poi effettuo il trimming alla selezione 
    definita, li combino e li mostro su DS9
    '''

    bias = separa(obs_list,'type','Bias', debug = debug)                    

    trim(bias, bias_dir, section = trim_section)                                                    

    combine(bias, '.tr', 'mbias', bias_dir, debug = debug)                    
    iraf.display(bias_dir+'mbias.fits',frame = 1)            

    print '############ Dark #############'

    '''
    Creazione dei master dark.

    Seleziono i dark dalla lista delle osservazioni, li stampo 
    in una lista su file da dare in paste a IRAF e li taglio. 
    Eseguo la correzione per bias e linearizzo tutte le immagini.

    '''

    dark = separa(obs_list,'type','Dark', debug = debug)                        
    trim(dark, dark_dir, section = trim_section, debug = debug)  
    print_list(dark, 'dark', main_dir = dark_dir, debug = debug)
    dark_list = hsel('@'+dark_dir+'dark', main_dir=dark_dir, debug = debug)                                   

    for item in dark_list['name']:
        operation(dark_dir+item+'.tr', bias_dir+'mbias.fits', '-', dark_dir+item+'.b', debug = debug)              
        linearize(dark_dir+item+'.b', dark_dir+item+'.l', debug = debug)

    '''
    individuo il numero di dark diversi effettuati, in base al
    tempo di esposizione. Combino poi solo i dark che hanno lo stesso
    tempo di esposizione. 
    '''

    exptime=[]
    for time in dark_list['texp']:                                            #controllo numero dark
        if time not in exptime:
            exptime.append(time)
    exptime=np.array(exptime)

    for time in exptime:                                                    
        lista_temp=[]
        for i in range(len(dark_list['texp'])):
            if dark_list['texp'][i]==time:                                    #seleziono i dark da combinare
                lista_temp.append(dark_list['name'][i])                

        out = 'dark%s.fits' % str(time)                                            #nomino il nuovo file
        if debug: print out
        combine(lista_temp, '.l', out, dark_dir, debug = debug)                #combino
        iraf.display(dark_dir+out,frame = 1)                                            #mostro

    os.remove(dark_dir+'dark')                                                #elimino la lista dei dark



    print '############ Flat ############'

    '''
    Creazione dei masterflat.

    Seleziono i flat dalla lista delle osservazioni.
    Per ogni filtro creo una variabile con il path della cartella dei
    flat. Correggo ogni immagine per bias e linearizzo. Bias 
    e flat stanno in cartelle diverse.
    '''

    flat = separa(obs_list,'type','Flat', debug = debug)                    #seleziono i flat
    print_list(flat, 'tmp_flats' , main_dir = main_dir)                         #creo lista per IRAF
    flat = hsel('@'+main_dir+'tmp_flats', main_dir = main_dir, debug = debug)
    os.remove(main_dir+'tmp_flats')

    for filtro in filtri:
        flat_dir = main_dir+filtro+'/flats/'                                #path cartella flat
        if os.listdir(flat_dir) == []:                                      #controlla che la cartella non sia vuota
            break 
        print '### Filtro %s' % filtro
        print '### Correzione per Bias'
        flat_list = separa(flat,'filter',filtro, debug = debug)
        print_list(flat_list, 'flats' , main_dir = flat_dir)                #creo lista per IRAF
        flat_list_filter = hsel('@'+flat_dir+'flats', main_dir = flat_dir, debug = debug)
        trim(flat_list_filter['name'], flat_dir, section = trim_section, debug = debug)

        for image in flat_list_filter['name']:                                      #sottraggo bias
            op1 = flat_dir+image+'.tr'                                      
            out = flat_dir+image+'.b'
            print '%s - %smbias %s' %(op1,bias_dir,out)
            operation(op1, bias_dir+'mbias', '-', out, debug = debug)
            out_l = flat_dir+image+'.l'
            linearize(out, out_l, debug = debug)                            #linearizzo i flat

        '''
        Normalizzazione dei flat e combinazione per ottenere il masterflat
        '''

        print '### Normalizzazione'

        flat_stats = stats(flat_list_filter['name'], '.l', flat_dir, debug = debug)                #mi calcolo la mediana per ogni flat
        for i in range(len(flat_list_filter)):                              #normalizzo i flat dividendo ciascuno per la sua mediana.
            op1 = flat_dir+flat_list_filter['name'][i]+'.l'
            out = flat_dir+flat_list_filter['name'][i]+'.n'
            print '%s / %i %s' %(op1,flat_stats[i],out)
            operation(op1, flat_stats[i], '/', out, debug = debug)
                                                                                    
        os.remove(flat_dir+'flats')                                                    #elimino il file

        combine(flat_list_filter['name'], '.n', 'mflat%s' %(filtro), flat_dir, debug = debug)       #combino tutti i flat nella cartella
        iraf.display(flat_dir+'mflat%s' %(filtro),frame = 1)
        print '################################################'


    print '############ Calibrazione oggetti ###############'

    '''
    Gli oggetti vengono ridotti in modalità standard.
    Prima vengono trimmati e corretti per bias.
    Tutte le immagini vengono poi linearizzate.
    Se ci sono i dark disponibili le immagini vengono corrette per dark
    e poi per flat.
    '''

    objects_list = separa(obs_list,'type','Object')                            #seleziono oggetti
    print_list(objects_list, 'tmp_obj' , main_dir = main_dir)                        #creo lista per IRAF
    objects_list = hsel('@'+main_dir+'tmp_obj', main_dir = main_dir, debug = debug)
    os.remove(main_dir+'tmp_obj')

    for filtro in filtri:
        flat_dir = main_dir+filtro+'/flats/'                                #per ogni filtro definisco la variabile con la cartella
        obj_dir = main_dir+filtro+'/objects/'                               #per ogni filtro definisco la variabile con la cartella
        if os.listdir(flat_dir) == []:
            break 
        obj_list = separa(objects_list,'filter',filtro)                         #seleziono solo i target con quel filtro
        print_list(obj_list, 'obj' , main_dir = obj_dir)                    #creo lista per IRAF
        obj_list_filter = hsel('@'+obj_dir+'obj', main_dir = obj_dir, debug = debug)
        trim(obj_list_filter['name'], obj_dir, section = trim_section)

        print '### Correzione Bias'
        for image in obj_list_filter['name']:
            op1 = obj_dir+image+'.tr'
            out = obj_dir+image+'.b'
            print '%s - %smbias %s' %(op1,bias_dir,out)
            operation(op1, bias_dir+'mbias', '-', out)                               # Correzione per Bias
            out_l = obj_dir+image+'.l'
            linearize(out, out_l, debug = debug)                            # linearizzo immagini scientifiche

        print '###Correzione Flat (& Dark)'
     
        for i in range(len(obj_list_filter['name'])):
            image = obj_list_filter['name'][i]
            if obj_list_filter['texp'][i] in exptime:
                op1 = obj_dir+image+'.l'
                out = obj_dir+image+'.d'                                
                print '%s - %sdark%s %s' %(op1,dark_dir,time, out)
                operation(op1, dark_dir+'dark%s' %(time), '-', out)              # Correzione per dark
                out2 = obj_dir+image+'.f'                               
                mflat = flat_dir+'mflat%s' %(filtro)
                print '%s / %s %s' %(out, mflat, out2)
                operation(out, mflat, '/', out2)                        # Correggo per flat
            else:
                op1 = obj_dir+image+'.l'
                out = obj_dir+image+'.f'                                
                mflat = flat_dir+'mflat%s' %(filtro)
                print '%s / %s %s' %(op1, mflat, out)
                operation(op1, mflat, '/', out)                        # Correggo per flat
        os.system('mkdir '+obj_dir+'final')
        os.system('mv '+obj_dir+'*.f.fits '+obj_dir+'final')
        print'###########################################'

if __name__ == '__main__':

    ################# Setting parameters################
    debug = False

    main_dir='./'               #definisco cartella principale

    trim_section = '[100:3996,100:3996]'                                    #decido la dimensione per il trimming

#    os.system('ds9&') 
    aa = pipeline(main_dir, trim_section, co1 = 1, co2 = -0.10140076, co3 = 0.034650755, debug = debug)






















