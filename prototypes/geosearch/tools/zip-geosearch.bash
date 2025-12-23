cd ../..
find -L geosearch -type f \( -name "*.webm" -o -name "*.jpg" -o -name "*.html" -o -name "transcription_answers.json" -o -name "index_*.json" \) -print0 | xargs -0 zip -r geosearch-$(date +%Y%m%d).zip
# Instructions
# Download the app & data zip file from Sharepoint (https://emckclac.sharepoint.com/sites/AHkdl/Shared%20Documents/Forms/AllItems.aspx?id=%2Fsites%2FAHkdl%2FShared%20Documents%2FIntelligent%20Systems%20for%20Screen%20Archives%20%2D%20exploring%20AI%20technologies%20through%20user%2Dcentred%20interaction%20in%20audiovisual%20archives%2FEXTERNAL%2FMaterials%20from%20KDL%2Fprototypes&viewid=da2edb6a%2D0c9c%2D4286%2D8086%2Da378514fc9c6)
# Unzip it
# Open a terminal under the geosearch folder and type the following command to start the web server
# python3 -m http.server 8080
# open http://localhost:8080/ with Firefox (unfortunately Chromium-based browsers won't play the videos properly)
