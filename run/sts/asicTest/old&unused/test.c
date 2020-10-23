void test(){
//TGraph* g1 = new TGraph("pulse_200_new.txt","%*lg%lg%lg");
//TGraph* g2 = new TGraph("pulse_200_new.txt","%*lg%lg%*lg%lg");
TGraph* g1 = new TGraph("pulse_50.txt","%*lg%lg%lg");
TGraph* g2 = new TGraph("pulse_50.txt","%*lg%lg%*lg%lg");

TFile* ofile = new TFile("test.root","RECREATE");
TTree* tree = new TTree("tree","tree") ;
int ch,adc,tdc;
tree->Branch("ch",&ch);
tree->Branch("adc",&adc);
tree->Branch("tdc",&tdc);


int N = g1->GetN() ;
for(int i=0;i<N;i++)
{
   double tmpx, tmpy;
   g1->GetPoint(i, tmpx, tmpy);
   ch = int(tmpx); adc = int(tmpy);
   g2->GetPoint(i, tmpx, tmpy);
   ch = int(tmpx); tdc = int(tmpy);

   tree->Fill();

}
ofile->cd();
tree->Write();
ofile->Close();

}
