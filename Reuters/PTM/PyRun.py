# Python code to reproduce experiments in the paper
import numpy as np
import funcs
import os

CODEPATH = '/home/hossein/Copy/ATDFinal/PTM'
trainingfile = '/home/hossein/Copy/ATDFinal/Reuters/data/trdocs.txt' #training data set
testfile = '/home/hossein/Copy/ATDFinal/Reuters/data/ntdocs.txt' #test data set
obs_tfile = '' #Observed data set
ho_tfile = '' # held-out data set
tr_label_file = '/home/hossein/Copy/ATDFinal/Reuters/data/trlbls.txt' #training class labels
t_label_file = '/home/hossein/Copy/ATDFinal/Reuters/data/ntlbls.txt' #test class labels
D = 2091#2357 # num of training documents
C = 646 # num of class labels
N = 9469#10283 # num of words
Mmax = 35#35 # Max num of topics
Mmin = 10 # Min num of topics
step = 1 # Topic reduction step size
seed0 = 1819114101
np.random.seed(seed0)

refile = open('results.dat', 'w+')
refile.write('M, bic, Etr_lkh, ho_lkh, avg_tpc/doc, avg_wrd/tpc, num_unq_wrds, tr_ccr, t_ccr, runtime, ')
refile.write('uv_avg_tpc/doc, uv_avg_wrd/tpc, uv_num_unq_wrds\n')
refile.close()

# replace class labels with integers
lbldic = {}
x = 0
fp = open(tr_label_file)
fp2 = open('tr_lbl.txt','w')
while True:
	line = fp.readline()
	if len(line)==0:
		break
	if line in lbldic:
		fp2.write(lbldic[line] + '\n')
	else:
		fp2.write(str(x) + '\n')
		lbldic.update({line:str(x)})
		x += 1
C = x
fp.close()
fp2.close()
fp = open(t_label_file)
fp2 = open('t_lbl.txt','w')
while True:
	line = fp.readline()
	if len(line)==0:
		break
	if line in lbldic:
		fp2.write(lbldic[line] + '\n')
	else:
		fp2.write('0\n') # put zero for classes that do not appear in the training set. (quick fix)
fp.close()
fp2.close()
tr_label_file = 'tr_lbl.txt'
t_label_file = 't_lbl.txt'

#main loop

k = reversed(range(Mmin,Mmax+step,step))
for M in k:
    path = 'dir' + str(M)
    ## run PTM on training data
    seed = np.random.randint(seed0)
    cmdtxt = CODEPATH + '/ptm --num_topics ' + str(M) + ' --corpus ' + trainingfile + ' --convergence 1e-4 --seed '+str(seed)
    if M == Mmax:
        cmdtxt = cmdtxt + ' --init seeded --dir ' + path
    else:
        cmdtxt = cmdtxt + ' --init load --model ' + path + '/init --dir ' + path 
    #if M <Mmax:# 25:
        #seed = np.random.randint(seed0)
        #continue
    os.system(cmdtxt)

    ### read training topic proportions
    theta = np.loadtxt(path+'/final.alpha')
    vswitch = np.loadtxt(path+'/final.v') 
    #read word probabilities
    beta = np.exp(np.loadtxt(path+'/final.beta'))
    uswitch = np.loadtxt(path+'/final.u') 
    for j in range(M):
        ind = np.where(uswitch[:,j]==0)[0]
        beta[ind,j+1] = beta[ind,0]
   
    
    # compute sparsity measures
    (avg_tpcs, avg_wrds, unq_wrds) = funcs.topic_word_sparsity(path+'/word-assignments.dat',N,M,uswitch)
    (uv_avg_tpcs, uv_avg_wrds, uv_unq_wrds) = funcs.switch_topic_word_sparsity(uswitch,vswitch,N,M)
    
    # read training likelihood
    lk = np.loadtxt(path+'/likelihood.dat')
    bic = lk[-1,0]
    lkh = lk[-1,1]
    runtime = lk[-1,3]

    # inference on test set
    seed = np.random.randint(seed0)
    cmdtxt = CODEPATH + '/ptm --task test' + ' --corpus ' + testfile + ' --convergence 1e-4 --seed '+str(seed)
    cmdtxt = cmdtxt + ' --dir ' + path + ' --model ' + path + '/final' 
    os.system(cmdtxt) 
      
    ## compute likelihood on training set
    Etrlk = funcs.compute_lkh(trainingfile, beta[:,1:M+1], theta)

    ### read test topic proportions
    theta_test = np.loadtxt(path+'/test.alpha')
    
    ## measure class label consistency
    (ccr_tr,tpc_lbl_distn) = funcs.classifier_training(tr_label_file,theta,C,M)
    ccr_t = funcs.classifier_test(t_label_file,tpc_lbl_distn,theta_test)
    
    
    ## save useful stuff
    # results file
    refile = open('results.dat', 'a')
    refile.write(str(M) + ', ' + str(bic) + ', ' + str(Etrlk) + ', ' + str(avg_tpcs) + ', ')
    refile.write(str(np.mean(avg_wrds)) + ', ' + str(np.sum(unq_wrds)) + ', ' + str(ccr_tr) + ', ' + str(ccr_t) + ', ')
    refile.write(str(runtime)+', '+str(uv_avg_tpcs) + ', ' + str(np.mean(uv_avg_wrds)) + ', ' + str(np.sum(uv_unq_wrds)) + '\n')
    refile.close()
    
    ## prepare for the next model order (writes it in the next folder)
    if  (M >= (Mmin+step)):
        next_path = 'dir' + str(M-step)
        os.system('mkdir -p '+next_path)
        funcs.prepare_next_forptm(step, path, next_path, theta)

    ## delete other files
    #os.system('rm -rf '+ path)
    
res = np.loadtxt('results.dat',skiprows=1,delimiter=',')
am = np.argmin(res[:,1])
print('M* = %d' % int(res[am,0]))
    