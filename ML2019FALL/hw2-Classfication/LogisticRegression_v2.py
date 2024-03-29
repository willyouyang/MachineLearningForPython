# HW2-Logistic Regression
import sys
import numpy as np
import pandas as pd
import csv
import matplotlib.pyplot as plt

### Parameters ###
RAWDATA_PATH = './dataset/train.csv'
OBSERVE_PATH = './dataset/test.csv'
SUBMISSION_PATH = './dataset/sample_submission.csv'
RAW_FEATURE_PATH = './dataset/X_train' # after proprecessing with raw data
RAW_LABEL_PATH = './dataset/Y_train'
OB_FEATURE_PATH = './dataset/X_test'
#RAWDATA_PATH = sys.argv[1]
#OBSERVE_PATH = sys.argv[2]
#SUBMISSION_PATH = sys.argv[3]
MODE_PATH = './model'
HIS_PATH = './history'
PIC_PATH = './picture'
##################

class Data():
    def __init__(self):
        self.data = {}
        self.feature = ['AMB_TEMP','CH4','CO','NMHC','NO','NO2','NOx','O3','PM10','PM2.5',
            'RAINFALL','RH','SO2','THC','WD_HR','WIND_DIREC','WIND_SPEED','WS_HR']
    # row : number of data as 'n', col : number of feature as 'm'
    def Read(self,name,path):
        with open(path,newline = '') as csvfile:
            rows = np.array(list(csv.reader(csvfile))[1:] ,dtype = float)  
            self.data[name] = rows # setting the data
            
# Data Processing - Normalization, One-hot encoding, discreate presentation
def Normalization(x,method='Rescaling',mean_or_max='None',std_or_min='None',trans=False):
    if trans == False:
        if method == 'Rescaling':
            mean_or_max = np.max(x,axis=0).reshape(1,-1)
            std_or_min = np.min(x,axis=0).reshape(1,-1)     
        elif method == 'Standardization':
            mean_or_max = np.mean(x, axis = 0).reshape(1,-1)
            std_or_min = np.std(x, axis = 0).reshape(1,-1)
    if method == 'Rescaling':
        x = (x - std_or_min) / (mean_or_max - std_or_min)
    elif method == 'Standardization':
        x = (x-mean_or_max) / std_or_min
    if trans:
        return x
    else:
        return x,mean_or_max,std_or_min
    
def Split_train_val(x,y,train_rate=0.7):
    perm = np.random.permutation(len(y)) # Shuffle
    x, y = x[perm], y[perm]
    split_pos = np.round(len(y)*train_rate).astype('int32')
    return x[:split_pos], x[split_pos:], y[:split_pos], y[split_pos:]            

def Fit(X,y,val=None,validation_split=0.0,bias=True,weights='zeros',
      loss='rmse',opt='vanilla',act='sigmoid',regularization=None,lamda=0.0001,
      learning_rate=0.001,decay='exp',decay_rate=1.0,
      epochs=1,batch_size=None,monitor='loss',patience=None,save_model=True):

    def initial(X,weights,bias):    
        dim = X.shape[1]
        if bias:
            dim = dim + 1
            X = np.concatenate((np.ones((X.shape[0],1)),X),axis=1).astype(float)
        if weights == 'zeros':
            w = np.zeros(shape=(dim, 1))
        elif weights == 'random':
            w = np.random.rand(dim, 1)
        return X, w
    
    # Activation 
    def activation(z,act):   
        if act == 'sigmoid':
            return np.clip(1 / (1.0 + np.exp(-z)), 1e-6, 1-1e-6) 
        else: # linear
            return z    
    
    def regular_term(mount,select,lamda,w):
        if mount == 'loss_value':
            if select == 'l1':
                reg = lamda * np.abs(w)
            elif select == 'l2':
                reg = lamda * np.abs(w)**2
            elif select == None:
                reg = np.zeros(w.shape)
            reg = reg.sum()
        elif mount == 'optimize':
            if select == 'l1':
                reg = lamda
            elif select == 'l2':
                reg = 2. * lamda * np.abs(w)
            elif select == None:
                reg = 0.
        return reg
    
    # Loss function      
    def loss_value(X,y,w,loss,act):
        reg = regular_term('loss_value',regularization,lamda,w)
        if loss == 'mse':
            pred = activation(X.dot(w),act)
            square_error = (y-pred)**2
            loss_value = square_error.sum()/len(y) # mse
        elif loss == 'rmse':
            pred = activation(X.dot(w),act)
            square_error = (y-pred)**2
            mse = square_error.sum()/len(y) # mse
            loss_value = np.power(mse,0.5) # rmse
        elif loss == 'cross_entropy':
            pred = activation(X.dot(w),act).reshape(1,-1)
            cross_entropy = -np.dot(np.log(pred),y)-np.dot(np.log(1-pred),(1-y)) # shape=(1,1)
            loss_value = cross_entropy[0] / len(y) # cross_entropy
        return (loss_value + reg)   

    # Optmize function
    def update_parameters(grad,w,sigma,m,opt,b1=0.9,b2=0.999):
        EPSILON = 1e-08 # To avoid thah sigma divied by nan or zero
        reg = regular_term('optimize',regularization,lamda,w)
        grad += reg
        if opt == 'ada':
            sigma += np.sqrt(grad**2)
            w -= grad * learning_rate / (sigma + EPSILON)
        elif opt == 'RMSProp':
            sigma = np.sqrt(b2 * sigma**2 + (1-b2) * grad**2)
            w -= grad * learning_rate / (sigma + EPSILON) 
        elif opt == 'Adam':
            m = (b1 * m + (1-b1) * grad) / (1-b1)
            sigma = np.sqrt((b2 * sigma + (1-b2) * grad**2) / (1-b2))
            w -= m * learning_rate / (sigma + EPSILON)
        else:
            m = b1 * m + (1-b1) * grad # momentum
            w -= m * learning_rate
        return w, sigma, m
            
    # Decay Learning rate
    def decay_learing_rate(lr,epoch,epochs,decay,decay_rate):
        if decay == 'exp':
            decay_lr = lr * decay_rate**(epochs/epoch)
        elif decay == 'natural_exp':
            decay_lr = lr * np.exp(-decay_rate*epochs/epoch)
        elif decay == 'sqrt':
            decay_lr = lr/np.sqrt(epoch)
        else:
            decay_lr = lr
        return decay_lr
    
    # Mini-batch
    def get_mini_batch(X,y,batch_size):
        mini_batches = []
        data = np.hstack((X,y))
        np.random.shuffle(data) 
        n_minibatches = data.shape[0] 
        for i in range(n_minibatches + 1): 
            mini_batch = data[i * batch_size:(i + 1)*batch_size, :] 
            X_mini = mini_batch[:, :-1] 
            Y_mini = mini_batch[:, -1].reshape((-1, 1)) 
            mini_batches.append((X_mini, Y_mini)) 
        if data.shape[0] % batch_size != 0: 
            mini_batch = data[i * batch_size:data.shape[0]] 
            X_mini = mini_batch[:, :-1] 
            Y_mini = mini_batch[:, -1].reshape((-1, 1)) 
            mini_batches.append((X_mini, Y_mini)) 
        return mini_batches

    # Split Training and Validation Set
    if val:
        X_t,X_v,y_t,y_v = Split_train_val(X,y,(1-validation_split))
    else:
        X_t,X_v,y_t,y_v = X,X,y,y
    
    # Fitting summary
    print('training sample:',len(X_t),' validation sample:',len(X_v))

    # Initialization
    X_t, w = initial(X_t,weights,bias)
    X_v, _ = initial(X_v,weights,bias)  
    
    ## Set model parameter
    sigma = None
    m = 0
    if opt == 'sgd':
        batch_size = 1
    elif opt == 'ada' or 'RMSProp' or 'Adam':
        sigma = np.zeros(w.shape)  
    # Mini-Batch Training    
    cost_history, acc_history = [], []
    see_best,see = None,0
    best_w = np.copy(w) # if we use '=', it will assign the same address.
    for epoch in range(1,epochs):
        # Shuffle 
        perm = np.random.permutation(len(y_t))
        X_t, y_t = X_t[perm], y_t[perm]
        
        # Update learning
        learning_rate = decay_learing_rate(learning_rate,epoch,epochs,decay,decay_rate)
        
        if batch_size == None:
                # Update weights
                w,sigma,m = update_parameters(X_t,y_t,w,sigma,m,opt)    
        # Mini-Batch Training
        else:
            mini_batches = get_mini_batch(X_t, y_t, batch_size)
            for i,mini_batch in enumerate(mini_batches): 
                X_mini, y_mini = mini_batch
                # Batch-Normalization
                batch_z = X_mini.dot(w)
                if i == 0:
                    batch_z,mean,std = Normalization(batch_z,'Standardization')
                else:
                    batch_z = Normalization(batch_z,'Standardization',mean,std,True)
                pred = activation(batch_z,act)
                grad = -2. * np.dot(X_mini.T,y_mini-pred)
                
                # Update weights
                w, sigma = update_parameters(grad,w,sigma,m,opt)
        # Cost
        cost = loss_value(X_t,y_t,w,loss,act) # on training set
        cost_v = loss_value(X_v,y_v,w,loss,act) # on validation ser
        cost_history.append((cost,cost_v))   
        # Accuracy 
        pred = activation(X_t.dot(w),act)
        classify = np.round(pred)
        acc = accuracy(classify, y_t)
        pred = activation(X_v.dot(w),act)
        classify = np.round(pred)
        acc_v = accuracy(classify, y_v)
        acc_history.append((acc,acc_v))
        print('Epoch:'+str(epoch) + '/' + str(epochs),'--loss: %.3f' % cost," val loss: %.3f" % cost_v, end=' ')
        print('--acc: %.3f' % acc,'-val_acc: %.3f' % acc_v)
        
        # Early Stopping - Avoid Overfitting
        if patience != None:
            see += 1
            if monitor == 'loss':
                moni = cost
            elif monitor == 'acc':
                moni = acc
            if see_best == None:
                see_best = np.round(moni,decimals=3)    
            elif see_best > cost:   
                see_best = np.round(moni,decimals=3)
                see = 0
                best_w = np.copy(w)
                continue
            elif see_best < cost:      
                print('The current'+monitor+'%.3f'%moni,'is not best than',see_best) 
                if see < patience:
                    continue
                else:
                    print('early stopping',see,'/',patience)
                    break
    # Save the best model
    if save_model != False:
        if patience != None:
            np.save(MODE_PATH+'/'+save_model+'_weight.npy',best_w) # save best weight
        else:
            np.save(MODE_PATH+'/'+save_model+'_weight.npy',w)
        np.save(HIS_PATH+'/'+save_model+'_history.npy',np.asarray(cost_history)) # save history
    return w, np.asarray(cost_history), np.asarray(acc_history)

def accuracy(pred, y):
    acc = np.sum(pred == y)/len(pred)
    return acc

def Plot_loss_history(history,save_model):
    plt.clf()
    loss_t, loss_v = history[:,0], history[:,1]
    plt.plot(loss_t,'b')
    plt.plot(loss_v,'r')
    if "loss" in save_model:
        plt.legend(['loss', 'val_loss'], loc="upper left")
        plt.ylabel("loss")
    elif "acc" in save_model:
        plt.legend(['acc', 'val_acc'], loc="upper left")
        plt.ylabel("acc")        
    plt.xlabel("epoch")
    plt.title("Training Process")
    if save_model == False:     
        plt.savefig(PIC_PATH+'/_history.png')
    else:
        plt.savefig(PIC_PATH+'/'+save_model+'_history.png')
    plt.show()
    plt.close()

def Sample():
    ## Read in raw data
    raw = Data()
    raw.Read('X_raw',RAW_FEATURE_PATH)
    raw.Read('y_raw',RAW_LABEL_PATH)
    col = [0,1,3,4,5]
    nor,mean,std = Normalization(raw.data['X_raw'][:,col])
    raw.data['X_raw'][:,col] = nor
    X_train, y_train = raw.data['X_raw'], raw.data['y_raw']
    
    ##  Training
    val=True
    validation_split=0.1155
    bias=True
    weights='zeros'
    loss='cross_entropy'
    opt='vanilla'
    act='sigmoid'
    regularization='l1'
    lamda= 0.001
    learning_rate=0.2
    decay='sqrt'
    decay_rate=1
    epochs=40
    batch_size=32
    monitor='acc'
    patience=None
    save_model='sample'
    
    model, cost_history, acc_history\
        = Fit(X_train,y_train,val,validation_split,bias,weights,
              loss,opt,act,regularization,lamda,learning_rate,
              decay,decay_rate,epochs,batch_size,
              monitor,patience,save_model)
    
#    ##Load model
#    model = np.load(MODE_PATH+'/'+save_model+'_weight.npy')

    ## Read in Observe set
    ob = Data()
    ob.Read('X_test',OB_FEATURE_PATH)
    ob.data['X_test'][:,col] = Normalization(ob.data['X_test'][:,col],'Rescaling',mean,std,trans=True)
    ob_X_p = ob.data['X_test']
    
    # Add the bias-term to ob_X_p
    if bias:
        ob_X_p = np.concatenate((np.ones(shape = (ob_X_p.shape[0],1)),ob_X_p),axis = 1).astype(float)
    ob_y_z = ob_X_p.dot(model)
    ob_y_p = np.clip(1 / (1.0 + np.exp(-ob_y_z)), 1e-6, 1-1e-6) 
    ob_y_c = np.round(ob_y_p)
    
    # Plot the history
    Plot_loss_history(cost_history,save_model+'_loss_')
    Plot_loss_history(acc_history,save_model+'_acc_')
    
    ## Write file
    with open(SUBMISSION_PATH,"w") as f:
        f.write('id,label\n') 
        for i,value in enumerate(ob_y_c):
            f.write('%d,%d\n' %(i+1, value))

if __name__ == '__main__':    
    Sample()