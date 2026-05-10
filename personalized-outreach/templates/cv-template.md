\documentclass[a4paper,10pt]{article}
\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage{tabularx}
\usepackage{geometry}
\geometry{left=1.2cm, top=1.2cm, right=1.2cm, bottom=1.2cm}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}
\titleformat{\section}{
\vspace{-5pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]
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
\href{mailto:==EMAIL==}{Email: \underline{==EMAIL==}} $|$
\href{==LINKEDIN URL==}{LinkedIn: \underline{==LINKEDIN NAME PROFILE==}} $|$
\href{==X URL==}{X: \underline{@==X PROFILE NAME==}} $|$
\href{==GITHUB URL==}{GitHub: \underline{==GITHUB NICKNAME==}}\\ \vspace{3pt}
\textbf{==PLACE==}
\end{center}

\section{SUMMARY}
==SHORT SUMMARY==

\section{Experience}
\resumeSubHeadingListStart
\resumeSubheading
{==POSITION TITLE== | ==COMPANY NAME==}{==WORKING PLACE==}
{==COMPANY DESCRIPTION==}{==WORK PERIOD==}
\resumeItemListStart
\resumeItem{==EXPERIENCE DESCRIPTION==}
\resumeItemListEnd
\resumeSubHeadingListEnd

\section{Projects}
\resumeSubHeadingListStart
\resumeProject
{==PROJECT NAME==}{==PROJECT PERIOD==}
\resumeItemListStart
\resumeItem{==PROJECT DESCRIPTION==}
\resumeItemListEnd
\resumeSubHeadingListEnd

\section{Public speaking}
\resumeSubHeadingListStart
\resumeItemListStart
\resumeItem{\textbf{\href{https://ethcc.io/archives/dapp-security-creating-a-trusted-web3-space}{\underline{ETHCC (Paris)}} \& \href{https://www.youtube.com/watch?v=6b46AoFdqxo}{\underline{DappCon (Berlin)}}:} Featured speaker on "Building trusted Web3 spaces" and "Overcoming UX friction in dapps"}
\resumeItem{\textbf{\href{https://www.youtube.com/watch?v=-gBAIC0lHbM}{\underline{ETH Dam (Amsterdam)}} \& \href{https://www.youtube.com/watch?v=ID3av0xJzKc}{\underline{ETH Belgrade}}:} Presented technical research on designing user-friendly zero-knowledge privacy tools}
\resumeItem{\textbf{\href{https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4787693}{\underline{DeFi privacy and self-regulatory compliance white paper}}:} Authored a white paper analyzing the intersection of zero-knowledge privacy and regulation, proposing a framework of selective disclosure and AML screening to mitigate illicit use in protocols like zkBob and RAILGUN}
\resumeItemListEnd
\resumeSubHeadingListEnd

\section{Skills}
\resumeSubHeadingListStart
\resumeItemListStart
\resumeItem{==TOOLS AND STACK==}
\resumeItemListEnd
\resumeSubHeadingListEnd

\section{Education}
\resumeSubHeadingListStart
\resumeSubheading
{Higher School of Economics}{GAP 8/10}
{Bachelor's degree, Computational and Applied Mathematics}{Sep 2016 -- Jun 2020}
\resumeSubHeadingListEnd

\end{document}
