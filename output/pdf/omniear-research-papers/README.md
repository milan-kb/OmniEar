# OmniEar research papers

This folder contains papers that directly support the OmniEar hackathon demo's claims about scream detection, transfer learning, environmental sound classification, and deployment on constrained edge devices.

License status was checked on 2026-08-19. Two papers have an explicit CC BY 4.0 redistribution license. Five additional PDFs were supplied by the repository owner and added at their direction; their inclusion does not imply that they are openly licensed. This is a practical repository record, not legal advice.

## Included PDFs

### Detecting Screams From Home Audio Recordings to Identify Tantrums

- Citation: O'Donovan, R., Sezgin, E., Bambach, S., Butter, E., and Lin, S. (2020). "Detecting Screams From Home Audio Recordings to Identify Tantrums: Exploratory Study Using Transfer Machine Learning." *JMIR Formative Research*, 4(6), e18279.
- DOI: https://doi.org/10.2196/18279
- Source: https://formative.jmir.org/2020/6/e18279/
- Copyright: © Rebecca O'Donovan, Emre Sezgin, Sven Bambach, Eric Butter, Simon Lin.
- License: CC BY 4.0 - https://creativecommons.org/licenses/by/4.0/
- Local file: `odonovan-2020-detecting-screams.pdf`
- Why it matters: This is the closest direct scientific precedent for OmniEar. It uses a pretrained AudioSet audio network and a downstream classifier to detect screams in noisy, real-world audio. It also reports the precision problem caused by rare scream events, which supports careful thresholding and false-positive controls.
- Changes made: None. The publisher PDF is redistributed unchanged.

### Environmental Sound Classification on the Edge

- Citation: Mohaimenuzzaman, M., Bergmeir, C., West, I. T., and Meyer, B. (2023). "Environmental Sound Classification on the Edge: A Pipeline for Deep Acoustic Networks on Extremely Resource-Constrained Devices." *Pattern Recognition*, 133, 109025.
- DOI: https://doi.org/10.1016/j.patcog.2022.109025
- Preprint source: https://arxiv.org/abs/2103.03483
- License: CC BY 4.0 - https://creativecommons.org/licenses/by/4.0/
- Local file: `mohaimenuzzaman-2023-environmental-sound-classification-edge.pdf`
- Why it matters: It provides evidence that accurate environmental sound classification can be compressed and deployed on small edge devices. This supports OmniEar's edge-inference and IoT deployment direction.
- Changes made: None. The arXiv PDF is redistributed unchanged.

## Owner-supplied PDFs

The following files were supplied and added by the repository owner. No explicit license permitting public repository redistribution was found during review. In particular, the AReN copy limits redistribution, the Handa copy states that IEEE restrictions apply, and the PANNs arXiv record uses arXiv's non-exclusive distribution license rather than a Creative Commons license. Repository maintainers should confirm that they have permission to publish these files.

1. Greco, A., Petkov, N., Saggese, A., and Vento, M. (2020). "AReN: A Deep Learning Approach for Sound Event Recognition Using a Brain Inspired Representation." *IEEE Transactions on Information Forensics and Security*, 15, 3610-3624. https://doi.org/10.1109/TIFS.2020.2994740
   - Local file: `greco-2020-aren.pdf`
   - Relevance: Deep sound-event recognition and robust acoustic representations.

2. Gemmeke, J. F., Ellis, D. P. W., Freedman, D., Jansen, A., Lawrence, W., Moore, R. C., Plakal, M., and Ritter, M. (2017). "Audio Set: An Ontology and Human-Labeled Dataset for Audio Events." *ICASSP 2017*, 776-780. https://doi.org/10.1109/ICASSP.2017.7952261
   - Official project page: https://research.google.com/audioset/
   - Local file: `gemmeke-2017-audioset.pdf`
   - Relevance: Defines the large-scale audio ontology and dataset behind YAMNet and many pretrained audio models.

3. Kong, Q., Cao, Y., Iqbal, T., Wang, Y., Wang, W., and Plumbley, M. D. (2020). "PANNs: Large-Scale Pretrained Audio Neural Networks for Audio Pattern Recognition." *IEEE/ACM Transactions on Audio, Speech, and Language Processing*, 28, 2880-2894. https://doi.org/10.1109/TASLP.2020.3030497
   - Preprint record: https://arxiv.org/abs/1912.10211
   - Local file: `kong-2020-panns.pdf`
   - Relevance: Strong scientific support for transfer learning from large audio datasets and pretrained embeddings.

4. Arnal, L. H., Flinker, A., Kleinschmidt, A., Giraud, A.-L., and Poeppel, D. (2015). "Human Screams Occupy a Privileged Niche in the Communication Soundscape." *Current Biology*, 25(15), 2051-2056. https://doi.org/10.1016/j.cub.2015.06.043
   - Free manuscript record: https://pmc.ncbi.nlm.nih.gov/articles/PMC4562283/
   - Local file: `arnal-2015-human-screams.pdf`
   - Relevance: Provides psychoacoustic backing for scream roughness, particularly temporal modulation around 30-150 Hz, and its relationship to rapid danger appraisal.

5. Handa, D., and Vig, R. (2020). "Distress Screaming vs Joyful Screaming: An Experimental Analysis on Both the High Pitch Acoustic Signals to Trace Differences and Similarities." *2020 Indo-Taiwan 2nd International Conference on Computing, Analytics and Networks*, 190-193. https://doi.org/10.1109/Indo-TaiwanICAN48429.2020.9181340
   - Local file: `handa-2020-distress-vs-joyful-screaming.pdf`
   - Relevance: Directly compares acoustic characteristics of distress and joyful screams, including intensity and duration.

## Citation-only paper

Flores-Salgado, B., Gonzalez-Ambriz, S.-J., Martinez-Garcia-Moreno, C.-A., and Beltran, J. (2024). "IoT-based system for campus community security." *Internet of Things*, 26, 101179. https://doi.org/10.1016/j.iot.2024.101179

- Relevance: Supports the campus-security and IoT monitoring use case.
- Not bundled: No supplied copy or openly licensed publisher or author PDF was found.

## Suggested scientific claims for the demo

- Pretrained audio embeddings can reduce the amount of task-specific training data needed for scream detection, but real-world validation and threshold calibration remain necessary.
- Rare-event detection should be evaluated with precision and recall, not accuracy alone, because background audio dominates the sample distribution.
- Human screams contain distinctive spectro-temporal roughness, but roughness should be treated as supporting evidence rather than a standalone threat label.
- Edge audio classification is technically feasible, including model compression and quantization for constrained devices.
- OmniEar is a hackathon prototype and should not be presented as a validated emergency-response or safety-critical system.
