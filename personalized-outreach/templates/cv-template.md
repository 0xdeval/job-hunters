\documentclass[a4paper,10pt]{article}
\usepackage{latexsym}
\usepackage{geometry}
\geometry{left=1.2cm, top=1.2cm, right=1.2cm, bottom=1.2cm}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage{tabularx}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}
\setcounter{secnumdepth}{0}

% Standard section redefinition for BasicTeX compatibility (replaces titlesec)
\makeatletter
\renewcommand{\section}{\@startsection{section}{1}{0pt}%
{-3.5ex plus -1ex minus -.2ex}%
{2.3ex plus .2ex}%
{\large\scshape\raggedright}}
\makeatother
\newcommand{\sectionRule}{\vspace{-5pt}\hrule\vspace{5pt}}
\newcommand{\resumeItem}[1]{
\item\small{
{#1 \vspace{-2pt}}
}
}
\newcommand{\resumeSubheading}[4]{
\vspace{8pt}\item
\begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
\textbf{#1} & #2 \\
\textit{\small#3} & \textit{\small #4} \\
\end{tabular*}\vspace{-5pt}
}
\newcommand{\resumeProject}[2]{
\item
\begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
\small\textbf{#1} & \small\textit{#2} \\
\end{tabular*}\vspace{-5pt}
}
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}[leftmargin=0.15in]}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

\begin{document}

\begin{center}
\textbf{\Huge \scshape ==PROFILE NAME==} \\ \vspace{5pt}
\small
==CONTACT_LINE==\\ \vspace{3pt}
\textbf{==PLACE==}
\end{center}

\section{SUMMARY}\sectionRule
==SHORT SUMMARY==

\section{Experience}\sectionRule
\resumeSubHeadingListStart
\resumeSubheading
{==POSITION TITLE== | ==COMPANY NAME==}{==WORKING PLACE==}
{==COMPANY DESCRIPTION==}{==WORK PERIOD==}
\resumeItemListStart
\resumeItem{==EXPERIENCE DESCRIPTION==}
\resumeItemListEnd
\resumeSubHeadingListEnd

\section{Projects}\sectionRule
\resumeSubHeadingListStart
\resumeProject
{==PROJECT NAME==}{==PROJECT PERIOD==}
\resumeItemListStart
\resumeItem{==PROJECT DESCRIPTION==}
\resumeItemListEnd
\resumeSubHeadingListEnd

==PUBLIC_SPEAKING_SECTION==

\section{Skills}\sectionRule
\resumeItemListStart
==TOOLS AND STACK==
\resumeItemListEnd

==EDUCATION_SECTION==

\end{document}
