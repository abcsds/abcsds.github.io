---
title: "Emotion analysis using heart rate data"
collection: publications
category: manuscripts
permalink: /publication/2019-emotion-analysis
excerpt: 'An attempt to classify human emotions without including Electroencephalography (EEG) signal, using the DEAP dataset (A Database for Emotion Analysis using Physiological Signals).'
date: 2019-08-29
venue: 'DEXA 2019'
slidesurl: 'http://abcsds.github.io/files/papers/2019_dexa.pdf'
paperurl: 'http://abcsds.github.io/files/papers/2019_dexa.pdf'
citation: 'Barradas Chacon, L. A., Fedoskin, A., Shcheglakova, E., Neamsup, S., & Rashed, A. (2019). Emotion analysis using heart rate data. In Database and Expert Systems Applications: DEXA 2019 International Workshops BIOKDD, IWCFS, MLKgraphs and TIR, Linz, Austria, August 26–29, 2019, Proceedings 30 (pp. 147-154). Springer International Publishing.'
---

This paper describes the attempt to classify human emotions without including Electroencephalography (EEG) signal, using the DEAP dataset (A Database for Emotion Analysis using Physiological Signals). Basing our research on the original paper (Koelstra et al. 2012), we claim that emotions (Valence and Arousal scores) can be classified with only one pulse detecting sensor with a comparable result to the classification based on the EEG signal. Moreover, we propose the method to classify emotions avoiding any sensors by extracting the pulse of the person from the video based on the head movements. Using Lucas-Kanade algorithm for optical flow (Balakrishnan et al. 2013), we extract movement signals, filter them, extract principal components, recreate heart rate (HR) signal and then use in the emotion classification. The first part of the project was conducted on the dataset containing 32 participants’ heart rate values (1280 activation cases), while the second part was based on the frontal videos of the participants (874 videos). Results support the idea of one-sensor emotion classification and deny the possibility of zero-sensor classification with the proposed method.