import React from 'react';
import { IonButton, IonIcon } from '@ionic/react';
import { downloadOutline } from 'ionicons/icons';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

interface PDFGeneratorProps {
  contentRef: React.RefObject<HTMLDivElement>;
}

const PDFGenerator: React.FC<PDFGeneratorProps> = ({ contentRef }) => {
  const generatePDF = async () => {
    if (contentRef.current) {
      const canvas = await html2canvas(contentRef.current);
      const imgData = canvas.toDataURL('image/png');

      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'px',
        format: 'a4'
      });

      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      const imgWidth = canvas.width;
      const imgHeight = canvas.height;
      const ratio = Math.min(pdfWidth / imgWidth, pdfHeight / imgHeight);
      const imgX = (pdfWidth - imgWidth * ratio) / 2;
      const imgY = 30;

      pdf.addImage(imgData, 'PNG', imgX, imgY, imgWidth * ratio, imgHeight * ratio);
      pdf.save('math-solution.pdf');
    }
  };

  return (
    <IonButton onClick={generatePDF} fill="outline" color="primary">
      <IonIcon slot="start" icon={downloadOutline} />
      Download as PDF
    </IonButton>
  );
};

export default PDFGenerator;