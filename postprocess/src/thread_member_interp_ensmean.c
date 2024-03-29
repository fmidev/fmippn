# define _BSD_SOURCE
# define _XOPEN_SOURCE 
# include <pthread.h>
# include <stdio.h>
# include <stdlib.h>
# include <time.h>
# include <math.h>
# include <string.h>
# include <unistd.h>
# include <limits.h>
# include <sys/types.h>
# include <stdint.h>
# include <ctype.h>
# include <hdf5.h>
# include <hdf5_hl.h>
# include <errno.h>

# define PAST 0
# define FUTU 1

# define handle_error_en(en, msg) do { errno = en; perror(msg); exit(EXIT_FAILURE); } while (0)
# define handle_error(msg) do { perror(msg); exit(EXIT_FAILURE); } while (0)

typedef struct  {    /* Used as argument to thread functions */
                      pthread_t TID;        /* ID returned by pthread_create() */
                      int member;  /* member index */
                      int tI;      /* timestep index */
                } ThreadInfo;

/* Global variables */

hid_t NcH5; /* Nowcast input HDF5 */
double ZR_A,ZR_B,AccScaler,gain,offset,vecscaler;
double **MotionData;
uint16_t nodata,newNodata,members,timesteps=0,intsteps=10;
uint16_t **pastZIarr,**futuZIarr,**pastZIarrPtr,**futuZIarrPtr;
uint16_t *Obsdata,**ObsArrPtr;
uint8_t dBZIfromIR[65536]={0};
uint8_t GENERATE_DBZ=0, GENERATE_INTER_ACC=0,USE_COMMON_MOTION=0;
uint8_t DETERMINISTIC=0; /* if deterministic "member" is stored */
uint8_t GENERATE_ENSMEAN=0,DETERM_ENSMEAN=0, DETERM_W=1;
uint16_t *ncZIfromObsZI;
uint8_t Ensmean_nodata=255;  
int32_t PGMscaler=1000,PGMscaler2,ZIveclen,intlen;
int32_t ***AccAverLUT;
int32_t **Accdata; /* [1/100000 mm] */
uint16_t *MeanAccdata; /* [1/100 mm] */
int32_t *AccFromZI;
int32_t ***trajecLUT[2],**OneStepMotion;
uint8_t **PGMAccdata,***dBZIdata;
long xsize,ysize,arrsize,fieldsize,motionfields=1;
char *outdir,*timestamp, nowcstamp[15];
time_t obsecs,dT,IdT;
double determ_initweight=0.0; /* Initial weight of deterministic nowcast, percent of amount of members */
  /* E.g. if iw=100, the weight of deterministic is equal to all memebers together */
double determ_weightspan=100.0; /* The weighting time span for deterministic nowcast, percent of max leadtime */
  /* E.g. if time is 200% the determ weight has dropped to half at the time of last timestep,
     if 50%, the weight drops to zero at the time of middle timestep. If negative, determ w is kept constant */  
double determ_startw, determ_lapse;
double determ_w; /* Actual weight of determ nowcast as a function of leadtime */

static void *trajecLUT_thread(void *arg);
static void *interpolation_thread(void *arg);
void date_from_sec(char *date,time_t secs);
time_t sec_from_date(char *date);
int H5get_variable_string(hid_t h5,char *datasetname, char *attrname, char *str);
uint8_t dBZIfromAcc(int32_t Acc);
void gen_ncZIfromObsZI_LUT(void);
void gen_dBZIfromIR_LUT(void);

/* ======================================== MAIN =================================================== */

int main(int argc, char *argv[])
{
   /* HDF5 variables */
  hid_t datatype;
  hsize_t dims[3];
  H5T_class_t class_id;
  size_t typesize;

  long SAMPLE = 1044550;
  int tI,mI,iI;
  char *p=NULL,datasetname[200];
  char *h5file,*obsfile,varstr[1000],accpref[100]="RAVACC",*Area=NULL;
  long N;
  double fnodata;

  setbuf(stdout,NULL);
  setbuf(stderr,NULL);
  H5Eset_auto(H5E_DEFAULT,NULL,NULL);

  timestamp=argv[1];
  h5file=argv[2];
  obsfile=argv[3];
  outdir=argv[4];
  Area=argv[5];
  if(argv[6]) intsteps=atoi(argv[6]);
  vecscaler=1.0/(double)intsteps;
  intlen=intsteps-1;

  /* Lisää ensmeanin env-muuttujat! */
  if(p=getenv("INTERP_NC_ACCPREF")) sprintf(accpref,"%s",p);
  if(p=getenv("INTERP_PGMSCALER")) PGMscaler=atol(p);
  if(p=getenv("INTERP_FORCED_TIMESTEPS")) timesteps=atoi(p);
  if(p=getenv("INTERP_SAMPLE_INDEX")) SAMPLE=atol(p); else SAMPLE=0;
  if(p=getenv("INTERP_GENERATE_DBZ")) if(strcasecmp(p,"TRUE")==0) GENERATE_DBZ=1;  
  if(p=getenv("INTERP_GENERATE_ENSMEAN")) if(strcasecmp(p,"TRUE")==0) GENERATE_ENSMEAN=1;  
  if(p=getenv("INTERP_GENERATE_INTER_ACC")) if(strcasecmp(p,"TRUE")==0) GENERATE_INTER_ACC=1;  
  if(p=getenv("INTERP_DETERM_INITWEIGHT")) determ_initweight = atof(p); 
  if(p=getenv("INTERP_DETERM_WEIGHTSPAN")) determ_weightspan = atof(p);
  if(p=getenv("INTERP_IGNORE_NODATA")) if(strcasecmp(p,"TRUE")==0) Ensmean_nodata=0;  

  PGMscaler2=2*PGMscaler;
  obsecs=sec_from_date(timestamp);

  /* ----------------------------------------------------------------------------------------------------------- */

  /* Open nowcast file and read configuration attributes */
  NcH5=H5Fopen(h5file, H5F_ACC_RDONLY, H5P_DEFAULT);

  if(H5get_variable_string(NcH5,"/meta/configuration","ZR_A",varstr) >= 0 )
     ZR_A=atof(varstr); else ZR_A=223.0;

  if(H5get_variable_string(NcH5,"/meta/configuration","ZR_B",varstr) >= 0 )
     ZR_B=atof(varstr); else ZR_B=1.53;

  if(H5get_variable_string(NcH5,"/meta/configuration","STORE_DETERMINISTIC",varstr) >= 0 )
    if(strcasecmp(varstr,"TRUE")==0) DETERMINISTIC=1; 

  if(H5get_variable_string(NcH5,"/meta/configuration","ENSEMBLE_SIZE",varstr) >= 0 )
     members=atoi(varstr)+DETERMINISTIC;

  if(H5get_variable_string(NcH5,"/meta/configuration","NOWCAST_TIMESTEP",varstr) >= 0 )
     dT=60*atoi(varstr); else dT=300; /* 5 min */

  if(H5get_variable_string(NcH5,"/meta/configuration","NUM_TIMESTEPS",varstr) >= 0 )
     if(!timesteps) timesteps=atoi(varstr); 

  if(H5get_variable_string(NcH5,"/meta/configuration","STORE_PERTURBED_MOTION",varstr) >= 0 )
     { if(strcasecmp(varstr,"True")==0) motionfields=members; else motionfields=1; }

  if(H5get_variable_string(NcH5,"/meta/configuration","VEL_PERT_KWARGS",varstr) >= 0 )
  {
     /* check if parallel and perpendicular motion perturbations are zero */  
     if(strcmp(varstr,"{'p_par': [0, 0, 0], 'p_perp': [0, 0, 0]}")==0)
        motionfields = 1;
  }

  if(motionfields==1) USE_COMMON_MOTION=1;

  printf("Motion fields %d\n",motionfields);

  IdT=dT/intsteps; /* interpolation timestep, default 30 seconds */

  /* Read data conversion attributes */  
  sprintf(datasetname,"/member-00/leadtime-00");
  H5LTget_attribute_double(NcH5,datasetname,"gain",&gain);
  H5LTget_attribute_double(NcH5,datasetname,"nodata",&fnodata);
  H5LTget_attribute_double(NcH5,datasetname,"offset",&offset);
  nodata=(uint16_t)(fnodata+1e-6);

  if(DETERMINISTIC)
  {
    if((determ_initweight <= 0.0) && (determ_weightspan <= 0.0)) DETERM_ENSMEAN=0;
    else {
            DETERM_ENSMEAN=1;
            determ_startw = 0.01*determ_initweight * (double)members;
            if(determ_weightspan <= 0.0) determ_lapse=0.0;
            else determ_lapse = 100.0*determ_startw/(determ_weightspan*(double)timesteps);
          /* Finally when use: determ_w = determ_startw - determ_lapse * (double)leadtI */
         }
  }

  /* ------------------------------------------------------------------------------------------------MOTION FIELDS--------- */


  /* Read motion fields and create LUT of trajectory source point indices for "from past" and 
     "from future" motion for each interpolation timestep index */
  {
     short tI,mI,iI;
     long csize;
     int ths,thread;
     ThreadInfo *ThInfo;
     pthread_attr_t th_attr;

     OneStepMotion = calloc(members,sizeof(int32_t *));
     MotionData=calloc(motionfields,sizeof(double *));
     datatype=H5T_IEEE_F64LE; /* for motion data */

     /* Initialize threading for trajectory LUT generation */
     ThInfo = calloc(motionfields, sizeof(ThreadInfo));
     ths = pthread_attr_init(&th_attr);
     if (ths != 0) handle_error_en(ths, "pthread_attr_init");

     /* Allocate trajectory LUT pointers */
     for(tI=PAST;tI<=FUTU;tI++) 
     {
        trajecLUT[tI] = calloc(members,sizeof(int32_t **));
        for(mI=0;mI<members;mI++) trajecLUT[tI][mI] = calloc(intlen,sizeof(int32_t *));
     }

     /* Loop thru motion fields (only one if common field, rest of member LUTs are pointers to common one) 
        and start a thread for each for LUT generation */

     for(mI=0;mI<motionfields;mI++)
     {
        if((motionfields==1) || (DETERMINISTIC && !mI)) sprintf(datasetname,"/motion");
        else sprintf(datasetname,"/member-%02d/motion",mI - DETERMINISTIC);

        if(!mI)
        {
           H5LTget_dataset_info(NcH5,datasetname, dims, &class_id, &typesize );
           csize=(long)dims[0];
           ysize=(long)dims[1];
           xsize=(long)dims[2];
           fieldsize=xsize*ysize;
           arrsize=fieldsize*csize;
        }
        OneStepMotion[mI] = malloc(fieldsize*sizeof(int32_t));
        MotionData[mI] = malloc(arrsize*typesize);
        H5LTread_dataset(NcH5,datasetname,datatype,MotionData[mI]);

        /* allocate trajectory LUTs */
        for(tI=PAST;tI<=FUTU;tI++) for(iI=0;iI<intlen;iI++) 
	   trajecLUT[tI][mI][iI] = calloc(fieldsize,sizeof(int32_t));

	/* starting thread for each motion field */
	printf("Starting trajectory LUT generation thread for motion field #%02d\n",mI);     
        ThInfo[mI].member = thread = mI;
        ths = pthread_create(&ThInfo[thread].TID, &th_attr, &trajecLUT_thread, &ThInfo[thread]);
        if (ths != 0) handle_error_en(ths, "pthread_create");
     }

     /* waiting threads to end */
     printf("Joining threads of trajectory LUT generation:\n");
     for(thread=0;thread<motionfields;thread++)
     {
        ths = pthread_join(ThInfo[thread].TID,NULL);
        if (ths != 0) handle_error_en(ths, "pthread_join");
	printf(" %02d",thread);
        free(MotionData[thread]);
     }         
     printf("\n\n");

     if(USE_COMMON_MOTION) /* If common motion field, set pointers of member LUTs to point member 0 LUT */
     {
         for(mI=1;mI<members;mI++)
	 {
            for(tI=PAST;tI<=FUTU;tI++) trajecLUT[tI][mI] = trajecLUT[tI][0];
            OneStepMotion[mI] = OneStepMotion[0];
	 }
     }

     ths = pthread_attr_destroy(&th_attr);
     if (ths != 0)  handle_error_en(ths, "pthread_attr_destroy");
     free(ThInfo);
     free(MotionData);
  }


  /* ---------------------------------------------------------------------------------------------ACCUMULATION LUT------- */

  /* Create LUT for accumulation per one nowcast timestep for each dBZI value pair */
  {
     double B,C,R,dBZ,Rscaler,k;
     int32_t zN,zN0,zN1,maxdBZ=100,maxN; /* maxN = 1320, jos gain=0.1 ja offset=-32 */
     int32_t Acc,Acc0,Acc1;
     int32_t X,rX,X1;
     int32_t IR; /* [1/100000 mm] */
  

     maxN = (maxdBZ-offset)/gain;
     
     newNodata = maxN+1;
     ZIveclen = newNodata+1;

     AccFromZI = calloc(ZIveclen,sizeof(int32_t));
     AccAverLUT = malloc(ZIveclen*sizeof(int32_t **));
    /* Conversion from intensity [mm/h] to accumulation during one IdT (interp timestep) 
       unit 1/100000 mm/IdT */
     Rscaler = dT/0.036/(double)intsteps; 
     AccScaler = Rscaler/269.0; 
     B = 0.1/ZR_B;
     C = log10(ZR_A)/ZR_B;

     /* zN -> Acc(dT) vector and memory allocations */

     /* printf("%d %f %d %d\n",intsteps, Rscaler, maxN, ZIveclen); */

     for(zN0=0;zN0<ZIveclen;zN0++)
     {
        AccAverLUT[zN0] = malloc(ZIveclen*sizeof(int32_t *));
        for(zN1=0;zN1<ZIveclen;zN1++) AccAverLUT[zN0][zN1]=calloc(intlen,sizeof(int32_t));        
        if(zN0)
	{
           dBZ = gain*(double)zN0+offset;
           R = pow(10.0,B*dBZ - C);
           IR = (int32_t)(R*Rscaler);
           AccFromZI[zN0]=IR;
	}
     }
     AccFromZI[maxN]=-1;
     /* printf("TOIMII 1\n"); */
  
     /* Linear interpolation of two timestep-accumulation over interp steps */
     for(zN0=1; zN0<ZIveclen; zN0++) 
     {
        Acc0=AccFromZI[zN0];
        for(zN1=zN0; zN1<ZIveclen; zN1++) 
        {
           Acc1=AccFromZI[zN1];
           k=(Acc1-Acc0)/(double)intsteps;
           for(X=0,X1=1,rX=intlen-1 ; X<intlen ; X++,X1++,rX--)        
	   {  
              if(zN0 == zN1) AccAverLUT[zN0][zN0][X] = Acc0;
              else
	      { 
		 Acc = (int32_t)(Acc0 + k*(double)X1);
                 AccAverLUT[zN0][zN1][X] = AccAverLUT[zN1][zN0][rX] = Acc;
              }
	   }
	}
     }

     /* Either value nodata */
     for(zN=0;zN<ZIveclen;zN++) for(X=0 ; X<intlen ; X++) 
         AccAverLUT[newNodata][zN][X] = AccAverLUT[zN][newNodata][X] = -1; 
  }

  /* -------------------------------------------------------------------------------------------DBZ/R LUTS------- */

  /* Create dBZI from rain rate LUT */
  gen_dBZIfromIR_LUT();

  /* Create obsdata to ncdata scale conversion LUT */
  gen_ncZIfromObsZI_LUT();

  /* -------------------------------------------------------------------------------------------READ OBSDATA----- */

  /* Read last observation dBZ PGM data. Both 8 and 16-bit IRIS style arrays accepted */
  {
     FILE *INPGM;
     int obsdyn=255,N,i;
     uint8_t *obsdata8=NULL;
     uint16_t dBZI,OBS8=0,*obsdata16=NULL;
     char hdr[256];     

     Obsdata=malloc(fieldsize*sizeof(uint16_t));

     printf("Reading the observed reflectivity field %s\n",obsfile);
     INPGM=fopen(obsfile,"r");
     for(i=0;i<3;i++)
     {
        memset(hdr,0,256);
        fgets(hdr,255,INPGM);
        if(hdr[0]=='#') { i--; continue; }
        if(i==2) obsdyn=atoi(hdr);
     }

     if(obsdyn>255)
     { 
        obsdata16=malloc(fieldsize*2);
        fread(obsdata16,1,fieldsize*2,INPGM);
        swab(obsdata16,obsdata16,fieldsize*2);
        OBS8=0;
     } 
     else
     { 
        obsdata8=malloc(fieldsize);
        fread(obsdata8,1,fieldsize,INPGM);
        OBS8=1;
     } 
     fclose(INPGM);

    /* Convert obsdata to nc-type data */
     for(N=0;N<fieldsize;N++)
     { 
        if(OBS8) dBZI=(uint16_t)obsdata8[N]; else dBZI=obsdata16[N];     
        dBZI=(uint16_t)obsdata8[N];        
        Obsdata[N] = ncZIfromObsZI[dBZI];
     }
     if(OBS8) free(obsdata8); else free(obsdata16);
  }

  /* --------------------------------------------------------------------------------------------ALLOCATIONS ----- */

  /* Allocations for interpolation arrays */

  if(GENERATE_DBZ) dBZIdata = calloc(members,sizeof(uint8_t **)); 
  if(GENERATE_INTER_ACC) PGMAccdata = calloc(members,sizeof(uint8_t *));
  datatype=H5T_STD_U16LE; /* For input nc data */

  Accdata   = calloc(members,sizeof(int32_t *));
  pastZIarr = calloc(members,sizeof(uint16_t *));
  futuZIarr = calloc(members,sizeof(uint16_t *));
  ObsArrPtr = calloc(members,sizeof(uint16_t *)); 
  MeanAccdata  = calloc(fieldsize,sizeof(int32_t));

  for(mI=0;mI<members;mI++)
  { 
     pastZIarr[mI] = malloc(fieldsize*sizeof(uint16_t));
     futuZIarr[mI] = malloc(fieldsize*sizeof(uint16_t));
     Accdata[mI] = calloc(fieldsize,sizeof(int32_t));
     if(GENERATE_INTER_ACC) PGMAccdata[mI] = malloc(fieldsize);
     if(GENERATE_DBZ) 
     {
        dBZIdata[mI]=malloc(intsteps*sizeof(uint8_t *));
        for(iI=0;iI<intsteps;iI++) dBZIdata[mI][iI]=malloc(fieldsize);
     }
     ObsArrPtr[mI] = Obsdata; /* because all members starts with the same observed data */ 
  }


  /* -------------------------------------------------------------------------------------------MAIN TIME LOOP---- */
  /* Main time loop */
  {
      char AccPath[255],MeanPath[255];
      FILE *ACCFILE,*MEANF;
      time_t ncsecs;
      uint16_t **tPtr; /* pointer for nc data array pointer swapping */
      long X,Y,N;
      int ths,thread;
      ThreadInfo *ThInfo;
      pthread_attr_t th_attr;
      double MeanAccsum,MeanCount,MembAcc;
     

      /* Initialize threading for member interpolation */
      ThInfo = calloc(members, sizeof(ThreadInfo));
      ths = pthread_attr_init(&th_attr);
      if (ths != 0) handle_error_en(ths, "pthread_attr_init");

      pastZIarrPtr = ObsArrPtr; /* First "past" data array is the observed data */
      futuZIarrPtr = futuZIarr;

      printf("Looping thru %d timesteps\n\n",timesteps);
      for(tI=0 ; tI<timesteps ; tI++)
      { 
	    ncsecs = dT*(tI+1);
            date_from_sec(nowcstamp,obsecs+ncsecs);
            if(DETERM_ENSMEAN)
	    {
                determ_w = determ_startw - determ_lapse * (double)tI; /* weight of deterministic "member" */ 
                if(determ_w < 0.0) DETERM_W = 0; 
	    }
	    /* Open RAVAKE-style accumulation file for all members for this timestep */
	    sprintf(AccPath,"%s/%s_%s-%.12s+%03d_%s.dat",outdir,accpref,timestamp,nowcstamp,(int)(ncsecs/60),Area);
	    ACCFILE=fopen(AccPath,"w");

	    printf("Processing accumulations for time %s, opening %s\n",nowcstamp,AccPath);

	    /* starting thread for each member */
	    for(mI=0 ; mI<members ; mI++)
	    {
	        if(!mI && DETERMINISTIC) sprintf(datasetname,"/deterministic/leadtime-%02d",tI);
		else sprintf(datasetname,"/member-%02d/leadtime-%02d",mI-DETERMINISTIC,tI);
		H5LTread_dataset(NcH5,datasetname,datatype,futuZIarrPtr[mI]);
		printf("Data of step %02d for member %02d read (%s), starting thread\n",tI,mI,datasetname);     
		for(N=0;N<fieldsize;N++) if(futuZIarrPtr[mI][N] == nodata) futuZIarrPtr[mI][N]=newNodata;

                ThInfo[mI].member = thread = mI;
                ThInfo[mI].tI = tI;

                ths = pthread_create(&ThInfo[thread].TID, &th_attr, &interpolation_thread, &ThInfo[thread]);
                if (ths != 0) handle_error_en(ths, "pthread_create");
	    }

            /* waiting threads to end */
            printf("Joining threads for step %02d, time %s:",tI,nowcstamp);
            for(thread=0;thread<members;thread++)
            {
               ths = pthread_join(ThInfo[thread].TID,NULL);
               if (ths != 0) handle_error_en(ths, "pthread_join");
              
               /* Write member accumulation data */
               mI = thread;
	       fwrite(Accdata[mI],1,fieldsize*sizeof(int32_t),ACCFILE);

	       printf(" %02d",mI);
            }
	    printf("\n\n");
	    fclose(ACCFILE);

            printf("Step %02d, time %s ready\n\n",tI,nowcstamp);

	    /* swap the "past" and "future" pointers of nowcast data arrays */
	    tPtr = pastZIarrPtr;
	    pastZIarrPtr = futuZIarrPtr;
	    if(tI) futuZIarrPtr = tPtr; else futuZIarrPtr = pastZIarr;

	    /* Generating ensemble mean accumulation, unit [1/100 mm] */
            if(GENERATE_ENSMEAN)
	    {
	       memset(MeanAccdata,Ensmean_nodata,fieldsize*sizeof(uint16_t));
               for(Y=0;Y<ysize;Y++) for(X=0;X<xsize;X++)
               {
	         N = Y*xsize+X;
                 MeanAccsum=0.0;
                 MeanCount=0.0;
                 for(mI=0;mI<members;mI++)
	         {
		    MembAcc=(double)Accdata[mI][N];
                    if(MembAcc>=0)
	            { 
		       if(DETERM_ENSMEAN && !mI)
		       {
			 if(DETERM_W)
			 {
                            MeanAccsum += MembAcc * determ_w;
                            MeanCount += determ_w;
			 }
		       } else 
		       {
                          MeanAccsum += MembAcc;
                          MeanCount += 1.0;
		       }
		    }
		 }
                 if(MeanCount>0) MeanAccdata[N]=(uint16_t)(0.001*MeanAccsum/MeanCount);
	       }
               swab(MeanAccdata,MeanAccdata,fieldsize*sizeof(uint16_t));
	       sprintf(MeanPath,"%s/Ensmean_%s-%.12s+%03d_%s.pgm",
                       outdir,timestamp,nowcstamp,(int)(ncsecs/60),Area);               
               MEANF=fopen(MeanPath,"w");
               fprintf(MEANF,"P5\n%ld %ld\n65535\n",xsize,ysize);
               fwrite(MeanAccdata,1,fieldsize*sizeof(uint16_t),MEANF);
               fclose(MEANF);
	    }

      } /* End of main time loop */

      ths = pthread_attr_destroy(&th_attr);
      if (ths != 0)  handle_error_en(ths, "pthread_attr_destroy");
      free(ThInfo);

  }
  H5Fclose(NcH5);

  printf("Interpolation of %s complete.\n",h5file);

  return(0);
}


/* ################################################################### FUNCTIONS ###################################### */


/* ============================================================================================  TRAJECTORY THREAD === */
/* Thread function of trajectory LUT generation for each motion field */

void *trajecLUT_thread(void *arg)
{
     ThreadInfo *Th_info = (ThreadInfo *) arg;
     double dX[2],dY[2],*MoData;
     int32_t N,Nv,motN,X,Y,iX,iY,oX,oY,iN,oN;
     short sig,wI[2],tI,mI,iI,wIT;
 
     mI=Th_info->member;
     MoData = MotionData[mI];

     /* Generate one nc timestep offset array pointing to past data */
     for(Y=0;Y<ysize;Y++) for(X=0;X<xsize;X++)
     { 
        N=Y*xsize+X;
        Nv=N+fieldsize; 

        oX = (int32_t)((double)X+0.5 - MoData[N]);
        oY = (int32_t)((double)Y+0.5 - MoData[Nv]);
        
        if(oX>=xsize ||
           oX<0      ||
           oY>=ysize ||
           oY<0       ) oN = -1;
        else oN = oY*xsize + oX; 
        OneStepMotion[mI][N]=oN;

        /* Scale motion vectors to interpolation time step length */
        MoData[N] *= vecscaler;
        MoData[Nv] *= vecscaler;
     } 

     /* Loop thru destination area */
     for(Y=0;Y<ysize;Y++) for(X=0;X<xsize;X++)
     {
           N=Y*xsize+X; 
 
           /* First step of trajectories (1/intstep of original motion vector) */
           dX[PAST] = dX[FUTU] = MoData[N];
           dY[PAST] = dY[FUTU] = MoData[N + fieldsize];

           /* Interpolation loop, begins one step from past field (obs field at start) */
           for(iI=0 ; iI<intlen ; iI++)
           {
	     /* weight (distance) indices */
	      wI[PAST]=iI;
              wI[FUTU]=intlen-iI-1;

	      for(tI=PAST,sig=-1 ; tI<=FUTU ; tI++,sig=1) /* trajectory "from past" has reverse motion field */
	      {
	         iX = (int32_t)((double)X+0.5 + (double)sig*dX[tI]);
	         iY = (int32_t)((double)Y+0.5 + (double)sig*dY[tI]);

	         /* If source pixel outside area, set trajectory source point array index to -1 */
                 if(iX>=xsize ||
                    iX<0      ||
                    iY>=ysize ||
                    iY<0        ) { iN = -1; motN = N; } 
                 else iN = motN = iY*xsize + iX;
	      /*
              if(SAMPLE) if(N==SAMPLE)
	      {
		printf("%d\t%d\t\tdX=%f\tdY=%f\tiX=%ld\tiY=%ld\tiN=%ld\n",tI,iI,dX[tI],dY[tI],iX,iY,iN); 
	      } 
	      */             
              /* trajectory increment */
                 dX[tI] += MoData[motN];
                 dY[tI] += MoData[motN + fieldsize];
                 /* Assign source point index iN and point's distance (weight) wI to destination LUT */
                 wIT=wI[tI];
                 trajecLUT[tI][mI][wIT][N] = iN;
	      }
           /* if(SAMPLE) if(N==SAMPLE) printf("\n"); */
	   }
     }

     return(NULL);
}

/* ======================================================================================= MEMBER INTERPOLATION THREAD ==== */
/*  ________________________Thread per nc timestep for interpolation ________ */

void *interpolation_thread(void *arg)
{
     ThreadInfo *Th_info = (ThreadInfo *) arg;
     int tI,iI,wI,mI;
     int32_t pastAcc,Acc,PGMAcc;
     uint16_t pastZI,futuZI;
     int32_t N,pastN,futuN,offN,X,Y;
     time_t ncsecs;
     char nowcstamp[15],intstamp[15];
     char outpath[250];
     FILE *OUTFILE;

     mI=Th_info->member;
     tI=Th_info->tI;;

     ncsecs=dT*(tI+1);
     date_from_sec(nowcstamp,obsecs+ncsecs);
     /* printf("Interpolating step %02d member %02d for time %s\n",tI,mI,nowcstamp); */

     /* reset monitor accumulation field */
     if(GENERATE_INTER_ACC) memset(PGMAccdata[mI],0,fieldsize);
     if(GENERATE_DBZ) for(iI=0;iI<intsteps;iI++) memset(dBZIdata[mI][iI],0,fieldsize);

        /* printf("INIT tI %d OK\n",tI); */

        /* Loop thru area */
     for(Y=0;Y<ysize;Y++) for(X=0;X<xsize;X++)
     {
	   N = pastN = Y*xsize+X; /* pixel index of "real time" data */

           /* Interpolation loop, begins with past data */ 
           for(iI=0,wI=-1; iI<intsteps ; iI++,wI++)        
	   {
	      Acc=0;
	      /* data pixel from past data */ 
	      if(wI>=0) pastN = trajecLUT[PAST][mI][wI][N];   /* trajectory starting point from past data  */

              if(pastN>=0)
	      {
                 pastZI = pastZIarrPtr[mI][pastN]; /* integer dBZ */
                 pastAcc = AccFromZI[pastZI];  /* conversion from dBZ to accumulation for one interpolation time step */
                 if(iI)
		 {
	            /* data pixel from future data */ 
                    futuN = trajecLUT[FUTU][mI][wI][N];
                    /* if(futuN>fieldsize && mI) printf("%d %d %d %d\t\t",mI,wI,pastN,futuN); */
                    if(futuN>=0)
		    {
                       futuZI = futuZIarrPtr[mI][futuN];
                       /* futuAcc = AccFromZI[futuZI]; no need to fetch */

                       /* time-weighted mean of past and future accumulation */
		       Acc  = AccAverLUT[pastZI][futuZI][wI];
		    } else Acc = -1;
		 } else Acc = pastAcc;
	      } else Acc = -1;

              if(GENERATE_DBZ) dBZIdata[mI][iI][N] = dBZIfromAcc(Acc);

              if(Acc>=0) Accdata[mI][N]+=Acc; else Accdata[mI][N]=-1;
# if 0
              if(SAMPLE) if(N==SAMPLE)
	      { 
		/* AAcc = pastAcc+iI*(futuAcc-pastAcc)/intsteps; */
                  printf("N: %ld %ld %ld\n",N,pastN,futuN);
		/*  printf("A: %ld\tpastZI=%04ld\tfutuZI=%04ld\tpastAcc=%04d\tfutuAcc=%04d\t\tAcc=%d\n",iI, pastZI, futuZI, pastAcc, futuAcc, Acc); */
                 /* printf("M: %ld\ttX=%04ld\ttY=%04ld\tsX=%04ld\tsY=%04ld\t\t%.3f\t%.3f\n",iI,tX,tY,sX,sY,fu,fv); */
	      }
# endif
           }

           /* Advect nodata area from past field to next future nc field (starts with advecting nodata from obs data) */
           offN = OneStepMotion[mI][N];
           if(offN<0 || pastZIarrPtr[mI][offN]==newNodata) futuZIarrPtr[mI][N]=newNodata;
     }
     /*     printf("Interpolated step  02%d member 02%d for time %s\n",tI,mI,nowcstamp); */

        /* create PGM data for monitoring if wanted */
        if(GENERATE_DBZ) for(iI=0;iI<intsteps;iI++)
        {
           date_from_sec(intstamp,obsecs + tI*dT + iI*IdT);
           sprintf(outpath,"%s/Z_M%02d_%s-%s.pgm",outdir,mI,timestamp,intstamp);
           OUTFILE=fopen(outpath,"w");
           fprintf(OUTFILE,"P5\n%ld %ld\n255\n",xsize,ysize);
           fwrite(dBZIdata[mI][iI],1,fieldsize,OUTFILE);
           fclose(OUTFILE);
	   /*           printf("dBZ data for memeber %d %s written\n",mI,intstamp); */
        }

        if(GENERATE_INTER_ACC) 
	{
           for(N=0;N<fieldsize;N++)
           { 
              if(Accdata[mI][N] < 0) { PGMAccdata[mI][N]=255; continue; }
              if(! Accdata[mI][N]) continue;
              if(Accdata[mI][N] < PGMscaler2) { PGMAccdata[mI][N]=1; continue; }
              PGMAcc = Accdata[mI][N]/PGMscaler;
              if(PGMAcc>250) PGMAccdata[mI][N]=255; else PGMAccdata[mI][N]=PGMAcc;
           }

           sprintf(outpath,"%s/Interacc_M%02d_%s-%s.pgm",outdir,mI,timestamp,nowcstamp);
           OUTFILE=fopen(outpath,"w");
           fprintf(OUTFILE,"P5\n%ld %ld\n255\n",xsize,ysize);
           fwrite(PGMAccdata[mI],1,fieldsize,OUTFILE);
           fclose(OUTFILE);
	}

	return(NULL);
}

/* =================================================================================================================== */


void date_from_sec(char *date,time_t secs)
{
   struct tm *Sdd;

   Sdd=gmtime(&secs);
   sprintf(date,"%d%02d%02d%02d%02d%02d",Sdd->tm_year+1900,Sdd->tm_mon+1,
                                         Sdd->tm_mday,Sdd->tm_hour,
	                                 Sdd->tm_min,Sdd->tm_sec);
   return;
}

/* ================================================================================================ */

time_t sec_from_date(char *date)
{
   struct tm Sd,*Sdd;
   int y,m;
   time_t secs;
 
   sscanf(date,"%4d%2d%2d%2d%2d",&y,&m,&Sd.tm_mday,&Sd.tm_hour,&Sd.tm_min);
   Sd.tm_year=y-1900;
   Sd.tm_mon=m-1;
   Sd.tm_isdst=0;
   Sd.tm_sec=0;
   Sdd=&Sd;
   secs=mktime(Sdd);
   return(secs);
}

/* ================================================================================================ */

int H5get_variable_string(hid_t h5,char *datasetname, char *attrname, char *str)
{
   hid_t dataset,attr,memtype,space;
   hvl_t  rdata;             /* Pointer to vlen structures */
   char *ptr;
   int i,len;
   /*
   int ndims,i,len;
   hsize_t dims[1] = {1};
   */
   herr_t status;

   memset(str,0,strlen(str));
   dataset=H5Dopen(h5,datasetname,H5P_DEFAULT);
   if(dataset<0) dataset=H5Gopen(h5,datasetname,H5P_DEFAULT);
   if(dataset<0) return(-1);
   attr = H5Aopen(dataset, attrname, H5P_DEFAULT);

   space = H5Aget_space(attr);
   memtype = H5Tvlen_create(H5T_NATIVE_CHAR);
   status = H5Aread(attr, memtype, &rdata);
   if(status<0) return(-1);
   ptr = rdata.p;
   len = rdata.len;
   for (i=0; i<len; i++) str[i]=ptr[i];
   str[i]=0;
   status = H5Dvlen_reclaim (memtype, space, H5P_DEFAULT, &rdata);
   status = H5Aclose (attr);
   status = H5Dclose (dataset);
   status = H5Sclose (space);
   status = H5Tclose (memtype);
   return(len);
}

/* ================================================================================================ */

uint8_t iRtodBZI(int32_t IR)
{
   int ZI;
   uint8_t dBZI;
   double R,dBZ; 

   if(!IR) dBZI=0;
   else
   {
      R=(double)IR;
      dBZ=10.0*log10(ZR_A*pow(R,ZR_B));
      if(dBZ > -32.0) ZI=(int)(2.0*dBZ)+64; else ZI=0;
      if(ZI > 254) ZI=254;
      dBZI=(uint8_t)ZI;
   }

    /*    printf("%d=%d ",R,dBZI); */
   return(dBZI);
}   

/* ================================================================================================ */

uint8_t dBZIfromAcc(int32_t Acc)
{
   int32_t IR;

   if(Acc<0) return(255);
   IR=(int32_t)((double)Acc/AccScaler);
   if(!IR) return(0);
   if(IR>=65535) return(255);
   return(dBZIfromIR[IR]);
}

/* ================================================================================================ */

  /* Create obsdata to ncdata scale conversion LUT */
void gen_ncZIfromObsZI_LUT(void)
{
     uint32_t N;
 
     ncZIfromObsZI = calloc(65536,sizeof(uint16_t));
     ncZIfromObsZI[255] = newNodata;
     ncZIfromObsZI[65535] = newNodata;
     /*
     ncZIfromObsZI[255] = 0;
     ncZIfromObsZI[65535] = 0;
     */
     for(N=1;N<255;N++) ncZIfromObsZI[N] = (uint16_t)((0.5*(double)N-32.0-offset)/gain); /* 1-byte IRIS dBZ */
     for(N=256;N<65535;N++) ncZIfromObsZI[N] = (uint16_t)((0.01*(double)N-327.68-offset)/gain); /* 2-byte IRIS dBZ */
}

/* ================================================================================================ */

void gen_dBZIfromIR_LUT(void)
{
   /* construct scaled R -> dBZI LUT here */
   int ZI;
   int32_t IR;
   uint8_t dBZI;
   double R,dBZ; 

   for(IR=1;IR<65535;IR++)
   {
      R=(double)IR/269.0;
      dBZ=10.0*log10(ZR_A*pow(R,ZR_B));
      if(dBZ > -32.0) ZI=(int)(2.0*dBZ)+64; else ZI=0;
      dBZI=(uint8_t)ZI;
      dBZIfromIR[IR]=dBZI;
   }
}   
